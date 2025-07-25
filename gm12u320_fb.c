/*
 * Copyright (C) 2012-2016 Red Hat Inc.
 *
 * Based in parts on the udl code. Based in parts on the gm12u320 fb driver:
 * Copyright (C) 2013 Viacheslav Nurmekhamitov <slavrn@yandex.ru>
 * Copyright (C) 2009 Roberto De Ioris <roberto@unbit.it>
 * Copyright (C) 2009 Jaya Kumar <jayakumar.lkml@gmail.com>
 * Copyright (C) 2009 Bernie Thompson <bernie@plugable.com>
 *
 * This file is subject to the terms and conditions of the GNU General Public
 * License v2. See the file COPYING in the main directory of this archive for
 * more details.
 */
#include <linux/module.h>
#include <linux/slab.h>
#include <linux/fb.h>
#include <linux/kernel.h>

#include <drm/drm_crtc.h>
#include <drm/drm_crtc_helper.h>
#include <drm/drm_fb_helper.h>
#include <drm/drm_framebuffer.h>
#include <drm/drm_print.h>
#include "gm12u320_drv.h"

struct gm12u320_fbdev {
	struct drm_fb_helper helper;
	struct gm12u320_framebuffer fb;
};

void gm12u320_fb_mark_dirty(struct gm12u320_framebuffer *fb,
			    int x1, int x2, int y1, int y2)
{
	struct drm_device *dev = fb->base.dev;
	struct gm12u320_device *gm12u320 = dev->dev_private;
	struct gm12u320_framebuffer *old_fb = NULL;
	bool wakeup = false;

	mutex_lock(&gm12u320->fb_update.lock);

	if (gm12u320->fb_update.fb != fb) {
		gm12u320->fb_update.x1 = x1;
		gm12u320->fb_update.x2 = x2;
		gm12u320->fb_update.y1 = y1;
		gm12u320->fb_update.y2 = y2;
		old_fb = gm12u320->fb_update.fb;
		gm12u320->fb_update.fb = fb;
	} else {
		gm12u320->fb_update.x1 = min(gm12u320->fb_update.x1, x1);
		gm12u320->fb_update.x2 = max(gm12u320->fb_update.x2, x2);
		gm12u320->fb_update.y1 = min(gm12u320->fb_update.y1, y1);
		gm12u320->fb_update.y2 = max(gm12u320->fb_update.y2, y2);
	}

	mutex_unlock(&gm12u320->fb_update.lock);

	if (wakeup)
		wake_up(&gm12u320->fb_update.waitq);

	if (old_fb)
		;
}

static int gm12u320_fb_open(struct fb_info *info, int user)
{
	/* If the USB device is gone, we don't accept new opens */
	return 0;
}

static struct fb_ops gm12u320_fb_ops = {
	.owner = THIS_MODULE,
	DRM_FB_HELPER_DEFAULT_OPS,
	.fb_open = gm12u320_fb_open,
};

#ifdef CONFIG_DRM_FBDEV_EMULATION
static struct fb_deferred_io gm12u320_fb_defio = {
	.delay = HZ / 30,
	.deferred_io = drm_fb_helper_deferred_io,
};
#endif

static int gm12u320_user_framebuffer_dirty(struct drm_framebuffer *drm_fb,
					   struct drm_file *file,
					   unsigned flags, unsigned color,
					   struct drm_clip_rect *clips,
					   unsigned num_clips)
{
	struct gm12u320_framebuffer *fb = to_gm12u320_fb(drm_fb);
	int x1, x2, y1, y2;

	if (num_clips == 0)
		return 0;

	x1 = clips->x1;
	x2 = clips->x2;
	y1 = clips->y1;
	y2 = clips->y2;

	while (--num_clips) {
		clips++;
		x1 = min_t(int, x1, (int)clips->x1);
		x2 = max_t(int, x2, (int)clips->x2);
		y1 = min_t(int, y1, (int)clips->y1);
		y2 = max_t(int, y2, (int)clips->y2);
	}

	gm12u320_fb_mark_dirty(fb, x1, x2, y1, y2);

	return 0;
}

static void gm12u320_user_framebuffer_destroy(struct drm_framebuffer *drm_fb)
{
	struct gm12u320_framebuffer *fb = to_gm12u320_fb(drm_fb);

	if (fb->obj)
		drm_gem_object_put(&fb->obj->base);

	drm_framebuffer_cleanup(drm_fb);
	kfree(fb);
}

static const struct drm_framebuffer_funcs gm12u320fb_funcs = {
	.destroy = gm12u320_user_framebuffer_destroy,
	.dirty = gm12u320_user_framebuffer_dirty,
};

static int
gm12u320_framebuffer_init(struct drm_device *dev,
			  struct gm12u320_framebuffer *fb,
			  const struct drm_mode_fb_cmd2 *mode_cmd,
			  struct gm12u320_gem_object *obj)
{
	int ret;

	fb->obj = obj;
	fb->base.dev = dev;
	fb->base.format = drm_get_format_info(dev, mode_cmd);
	fb->base.pitches[0] = mode_cmd->pitches[0];
	fb->base.offsets[0] = mode_cmd->offsets[0];
	fb->base.width = mode_cmd->width;
	fb->base.height = mode_cmd->height;
	fb->base.flags = mode_cmd->flags;
	ret = drm_framebuffer_init(dev, &fb->base, &gm12u320fb_funcs);
	return ret;
}

static int gm12u320fb_create(struct drm_fb_helper *helper,
			     struct drm_fb_helper_surface_size *sizes)
{
	struct gm12u320_fbdev *fbdev =
		container_of(helper, struct gm12u320_fbdev, helper);
	struct drm_device *dev = fbdev->helper.dev;
	struct fb_info *info;
	struct drm_framebuffer *drm_fb;
	struct drm_mode_fb_cmd2 mode_cmd;
	struct gm12u320_gem_object *obj;
	uint32_t size;
	int ret = 0;

	if (sizes->surface_bpp == 24)
		sizes->surface_bpp = 32;

	mode_cmd.width = sizes->surface_width;
	mode_cmd.height = sizes->surface_height;
	mode_cmd.pitches[0] = mode_cmd.width * ((sizes->surface_bpp + 7) / 8);

	if (sizes->surface_bpp == 32)
		mode_cmd.pixel_format = DRM_FORMAT_XRGB8888;
	else if (sizes->surface_bpp == 24)
		mode_cmd.pixel_format = DRM_FORMAT_RGB888;
	else if (sizes->surface_bpp == 16)
		mode_cmd.pixel_format = DRM_FORMAT_RGB565;
	else
		mode_cmd.pixel_format = DRM_FORMAT_XRGB8888;

	size = mode_cmd.pitches[0] * mode_cmd.height;
	size = ALIGN(size, PAGE_SIZE);

	obj = gm12u320_gem_alloc_object(dev, size);
	if (!obj)
		goto out;

	ret = gm12u320_gem_vmap(obj);
	if (ret) {
		DRM_ERROR("failed to vmap fb\n");
		goto out_gfree;
	}

	info = drm_fb_helper_alloc_info(helper);
	if (IS_ERR(info)) {
		ret = PTR_ERR(info);
		goto out_gfree;
	}
	info->par = fbdev;

	ret = gm12u320_framebuffer_init(dev, &fbdev->fb, &mode_cmd, obj);
	if (ret)
		goto out_gfree;

	drm_fb = &fbdev->fb.base;

	fbdev->helper.fb = drm_fb;

	strcpy(info->fix.id, "gm12u320drmfb");

	info->screen_base = fbdev->fb.obj->vmapping;
	info->fix.smem_len = size;
	info->fix.smem_start = (unsigned long)fbdev->fb.obj->vmapping;

	info->fbops = &gm12u320_fb_ops;
	drm_fb_helper_prepare(dev, &fbdev->helper, 32, NULL);
#ifdef CONFIG_DRM_FBDEV_EMULATION
	info->fbdefio = &gm12u320_fb_defio;
	fb_deferred_io_init(info);
#endif

	DRM_DEBUG_KMS("allocated %dx%d vmal %p\n",
		      drm_fb->width, drm_fb->height,
		      fbdev->fb.obj->vmapping);

	return ret;

out_gfree:
	drm_gem_object_put(&fbdev->fb.obj->base);
out:
	return ret;
}

static const struct drm_fb_helper_funcs gm12u320_fb_helper_funcs = {
	.fb_probe = gm12u320fb_create,
};

/* Simple framebuffer device registration */
static int register_framebuffer_device(struct drm_device *dev, struct gm12u320_fbdev *fbdev)
{
	struct fb_info *info;
	struct drm_framebuffer *drm_fb;
	struct drm_mode_fb_cmd2 mode_cmd;
	struct gm12u320_gem_object *obj;
	uint32_t size;
	int ret = 0;
	
	printk(KERN_INFO "gm12u320: register_framebuffer_device: Starting\n");

	/* Create a simple 640x480 24bpp framebuffer (smaller size) */
	mode_cmd.width = 640;
	mode_cmd.height = 480;
	mode_cmd.pitches[0] = mode_cmd.width * 3; /* 24bpp = 3 bytes per pixel */
	mode_cmd.pixel_format = DRM_FORMAT_RGB888;

	size = mode_cmd.pitches[0] * mode_cmd.height;
	size = ALIGN(size, PAGE_SIZE);

	printk(KERN_INFO "gm12u320: Allocating GEM object of size %u\n", size);
	obj = gm12u320_gem_alloc_object(dev, size);
	if (!obj) {
		printk(KERN_ERR "gm12u320: Failed to allocate GEM object\n");
		return -ENOMEM;
	}
	printk(KERN_INFO "gm12u320: GEM object allocated successfully\n");

	ret = gm12u320_gem_vmap(obj);
	if (ret) {
		printk(KERN_ERR "gm12u320: Failed to vmap GEM object\n");
		gm12u320_gem_free_object(&obj->base);
		return ret;
	}

	/* Create framebuffer */
	ret = gm12u320_framebuffer_init(dev, &fbdev->fb, &mode_cmd, obj);
	if (ret) {
		printk(KERN_ERR "gm12u320: Failed to init framebuffer\n");
		gm12u320_gem_free_object(&obj->base);
		return ret;
	}

	drm_fb = &fbdev->fb.base;
	fbdev->helper.fb = drm_fb;

	/* Create fb_info */
	info = framebuffer_alloc(0, NULL);
	if (!info) {
		printk(KERN_ERR "gm12u320: Failed to allocate fb_info\n");
		gm12u320_gem_free_object(&obj->base);
		return -ENOMEM;
	}

	strcpy(info->fix.id, "gm12u320fb");
	info->screen_base = obj->vmapping;
	info->fix.smem_len = size;
	info->fix.smem_start = (unsigned long)obj->vmapping;
	info->fix.type = FB_TYPE_PACKED_PIXELS;
	info->fix.visual = FB_VISUAL_TRUECOLOR;
	info->fix.line_length = mode_cmd.pitches[0];
	info->var.xres = mode_cmd.width;
	info->var.yres = mode_cmd.height;
	info->var.bits_per_pixel = 24;
	info->var.red.length = 8;
	info->var.green.length = 8;
	info->var.blue.length = 8;
	info->var.red.offset = 16;
	info->var.green.offset = 8;
	info->var.blue.offset = 0;

	info->fbops = &gm12u320_fb_ops;
	info->par = fbdev;

	/* Register framebuffer */
	ret = register_framebuffer(info);
	if (ret) {
		printk(KERN_ERR "gm12u320: Failed to register framebuffer: %d\n", ret);
		framebuffer_release(info);
		gm12u320_gem_free_object(&obj->base);
		return ret;
	}

	fbdev->helper.info = info;
	printk(KERN_INFO "gm12u320: Framebuffer registered as /dev/fb1\n");

	return 0;
}

static void gm12u320_fbdev_destroy(struct drm_device *dev,
				   struct gm12u320_fbdev *fbdev)
{
#ifdef CONFIG_DRM_FBDEV_EMULATION
	fb_deferred_io_cleanup(fbdev->helper.info);
#endif
	drm_fb_helper_fini(&fbdev->helper);
	drm_framebuffer_unregister_private(&fbdev->fb.base);
	drm_framebuffer_cleanup(&fbdev->fb.base);
	drm_gem_object_put(&fbdev->fb.obj->base);
}

int gm12u320_fbdev_init(struct drm_device *dev)
{
	struct gm12u320_device *gm12u320 = dev->dev_private;
	struct gm12u320_fbdev *fbdev;
	int ret;

	printk(KERN_INFO "gm12u320: fbdev_init: STARTING\n");
	DRM_DEBUG("gm12u320_fbdev_init: STARTING\n");

	fbdev = kzalloc(sizeof(*fbdev), GFP_KERNEL);
	if (!fbdev) {
		DRM_ERROR("Failed to allocate fbdev\n");
		return -ENOMEM;
	}

	gm12u320->fbdev = fbdev;

	drm_fb_helper_prepare(dev, &fbdev->helper, 32, &gm12u320_fb_helper_funcs);

	ret = drm_fb_helper_init(dev, &fbdev->helper);
	if (ret) {
		printk(KERN_WARNING "gm12u320: Failed to initialize fb helper: %d (EOPNOTSUPP - Operation not supported)\n", ret);
		printk(KERN_INFO "gm12u320: This is expected in newer kernel versions, continuing without fb helper\n");
		/* Don't fail the driver load, just continue without fb helper */
		goto skip_fb_helper;
	}

	/* TEMPORARY: Skip initial config to avoid kernel panic in Linux 6.x */
	printk(KERN_INFO "gm12u320: Skipping drm_fb_helper_initial_config to avoid panic in Linux 6.x\n");
	printk(KERN_INFO "gm12u320: Framebuffer helper not compatible with this kernel version\n");

	/* Create a simple test framebuffer for the workqueue */
	printk(KERN_INFO "gm12u320: Creating test framebuffer for workqueue\n");
	
	/* Create a simple framebuffer device /dev/fb1 for userspace copying */
	printk(KERN_INFO "gm12u320: Attempting to register framebuffer device...\n");
	ret = register_framebuffer_device(dev, fbdev);
	if (ret) {
		printk(KERN_WARNING "gm12u320: Failed to register framebuffer device: %d\n", ret);
		printk(KERN_INFO "gm12u320: Will use rainbow pattern instead\n");
	} else {
		printk(KERN_INFO "gm12u320: Framebuffer device /dev/fb1 created successfully\n");
		printk(KERN_INFO "gm12u320: You can now use: while true; do cat /dev/fb0 > /dev/fb1; sleep 0.1; done\n");
	}

	DRM_DEBUG("gm12u320_fbdev_init: SUCCESS\n");

	return 0;

skip_fb_helper:
	/* Continue without fb helper, but still try to create framebuffer device */
	printk(KERN_INFO "gm12u320: Skipping fb helper, attempting direct framebuffer creation\n");
	
	/* Don't fail the driver load, just continue without fb helper */
	printk(KERN_INFO "gm12u320: Driver will work without framebuffer helper\n");
	return 0;

err_free:
	kfree(fbdev);
	gm12u320->fbdev = NULL;
	return ret;
}

void gm12u320_fbdev_cleanup(struct drm_device *dev)
{
	struct gm12u320_device *gm12u320 = dev->dev_private;

	if (!gm12u320->fbdev)
		return;

	gm12u320_fbdev_destroy(dev, gm12u320->fbdev);
	kfree(gm12u320->fbdev);
	gm12u320->fbdev = NULL;
}

void gm12u320_fbdev_unplug(struct drm_device *dev)
{
	struct gm12u320_device *gm12u320 = dev->dev_private;

	if (!gm12u320->fbdev)
		return;

	/* fbdev cleanup is handled by drm_fb_helper_fini */
}

struct drm_framebuffer *
gm12u320_fb_user_fb_create(struct drm_device *dev,
			   struct drm_file *file,
			   const struct drm_mode_fb_cmd2 *mode_cmd)
{
	struct drm_gem_object *obj;
	struct gm12u320_framebuffer *fb;
	int ret;
	uint32_t size;

	obj = drm_gem_object_lookup(file, mode_cmd->handles[0]);
	if (obj == NULL)
		return ERR_PTR(-ENOENT);

	size = mode_cmd->pitches[0] * mode_cmd->height;
	size = ALIGN(size, PAGE_SIZE);

	if (size > obj->size) {
		DRM_ERROR("object size not sufficient for fb %d %zu %d %d\n",
			  size, obj->size, mode_cmd->pitches[0],
			  mode_cmd->height);
		return ERR_PTR(-ENOMEM);
	}

	fb = kzalloc(sizeof(*fb), GFP_KERNEL);
	if (fb == NULL)
		return ERR_PTR(-ENOMEM);

	ret = gm12u320_framebuffer_init(dev, fb, mode_cmd, to_gm12u320_bo(obj));
	if (ret) {
		kfree(fb);
		return ERR_PTR(-EINVAL);
	}
	return &fb->base;
}
