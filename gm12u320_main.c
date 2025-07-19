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
#include <linux/kernel.h>
#include <linux/dma-buf.h>
#include <drm/drm_drv.h>
#include <drm/drm_vblank.h>
#include "gm12u320_drv.h"

/* Function prototypes */
void gm12u320_32bpp_to_24bpp_packed(u8 *dst, u8 *src, int len);

/* Timer function to start fb update safely */
static void gm12u320_fb_update_timer(struct timer_list *t);

static bool eco_mode;
module_param(eco_mode, bool, 0644);
MODULE_PARM_DESC(eco_mode, "Turn on Eco mode (less bright, more silent)");

#define MISC_RCV_EPT			1
#define DATA_RCV_EPT			2
#define DATA_SND_EPT			3
#define MISC_SND_EPT			4

#define DATA_BLOCK_HEADER_SIZE		84
#define DATA_BLOCK_CONTENT_SIZE		64512
#define DATA_BLOCK_FOOTER_SIZE		20
#define DATA_BLOCK_SIZE			(DATA_BLOCK_HEADER_SIZE + \
					 DATA_BLOCK_CONTENT_SIZE + \
					 DATA_BLOCK_FOOTER_SIZE)
#define DATA_LAST_BLOCK_CONTENT_SIZE	4032
#define DATA_LAST_BLOCK_SIZE		(DATA_BLOCK_HEADER_SIZE + \
					 DATA_LAST_BLOCK_CONTENT_SIZE + \
					 DATA_BLOCK_FOOTER_SIZE)

#define CMD_SIZE			31
#define READ_STATUS_SIZE		13
#define MISC_VALUE_SIZE			4

#define CMD_TIMEOUT			200
#define DATA_TIMEOUT			1000
#define IDLE_TIMEOUT			2000
#define FIRST_FRAME_TIMEOUT		2000

#define MISC_REQ_GET_SET_ECO_A		0xff
#define MISC_REQ_GET_SET_ECO_B		0x35
/* Windows driver does once evert second, with with arg d = 1, others 0 */
#define MISC_REQ_UNKNOWN1_A		0xff
#define MISC_REQ_UNKNOWN1_B		0x38
/* Windows driver does this on init, with arg a, b = 0, c = 0xa0, d = 4 */
#define MISC_REQ_UNKNOWN2_A		0xa5
#define MISC_REQ_UNKNOWN2_B		0x00

static const char cmd_data[CMD_SIZE] = {
	0x55, 0x53, 0x42, 0x43, 0x00, 0x00, 0x00, 0x00,
	0x68, 0xfc, 0x00, 0x00, 0x00, 0x00, 0x10, 0xff,
	0x00, 0x00, 0x00, 0x00, 0xfc, 0x00, 0x80, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

static const char cmd_draw[CMD_SIZE] = {
	0x55, 0x53, 0x42, 0x43, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0xfe,
	0x00, 0x00, 0x00, 0xc0, 0xd1, 0x05, 0x00, 0x40,
	0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00
};

static const char cmd_misc[CMD_SIZE] = {
	0x55, 0x53, 0x42, 0x43, 0x00, 0x00, 0x00, 0x00,
	0x04, 0x00, 0x00, 0x00, 0x80, 0x01, 0x10, 0xfd,
	0x00, 0x00, 0x00, 0xc0, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

static const char data_block_header[DATA_BLOCK_HEADER_SIZE] = {
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0xfb, 0x14, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x04, 0x15, 0x00, 0x00, 0xfc, 0x00, 0x00,
	0x01, 0x00, 0x00, 0xdb
};

static const char data_last_block_header[DATA_BLOCK_HEADER_SIZE] = {
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0xfb, 0x14, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x2a, 0x00, 0x20, 0x00, 0xc0, 0x0f, 0x00, 0x00,
	0x01, 0x00, 0x00, 0xd7
};

static const char data_block_footer[DATA_BLOCK_FOOTER_SIZE] = {
	0xfb, 0x14, 0x02, 0x20, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x80, 0x00, 0x00, 0x4f
};

static int gm12u320_usb_alloc(struct gm12u320_device *gm12u320)
{
	int i, block_size;
	const char *hdr;

	printk(KERN_INFO "gm12u320: Allocating USB buffers\n");
	
	gm12u320->cmd_buf = kmalloc(CMD_SIZE, GFP_KERNEL);
	if (!gm12u320->cmd_buf) {
		printk(KERN_ERR "gm12u320: Failed to allocate cmd_buf\n");
		return -ENOMEM;
	}
	printk(KERN_INFO "gm12u320: cmd_buf allocated at %p\n", gm12u320->cmd_buf);

	for (i = 0; i < GM12U320_BLOCK_COUNT; i++) {
		if (i == GM12U320_BLOCK_COUNT - 1) {
			block_size = DATA_LAST_BLOCK_SIZE;
			hdr = data_last_block_header;
		} else {
			block_size = DATA_BLOCK_SIZE;
			hdr = data_block_header;
		}

		gm12u320->data_buf[i] = kzalloc(block_size, GFP_KERNEL);
		if (!gm12u320->data_buf[i]) {
			printk(KERN_ERR "gm12u320: Failed to allocate data_buf[%d]\n", i);
			return -ENOMEM;
		}
		printk(KERN_INFO "gm12u320: data_buf[%d] allocated at %p\n", i, gm12u320->data_buf[i]);

		memcpy(gm12u320->data_buf[i], hdr, DATA_BLOCK_HEADER_SIZE);
		memcpy(gm12u320->data_buf[i] +
				(block_size - DATA_BLOCK_FOOTER_SIZE),
		       data_block_footer, DATA_BLOCK_FOOTER_SIZE);
	}

	printk(KERN_INFO "gm12u320: USB buffers allocated successfully\n");
	return 0;
}

static void gm12u320_usb_free(struct gm12u320_device *gm12u320)
{
	int i;

	for (i = 0; i < GM12U320_BLOCK_COUNT; i++)
		kfree(gm12u320->data_buf[i]);

	kfree(gm12u320->cmd_buf);
}

static int gm12u320_misc_request(struct gm12u320_device *gm12u320,
				 u8 req_a, u8 req_b,
				 u8 arg_a, u8 arg_b, u8 arg_c, u8 arg_d)
{
	int ret, len;
	u8 *buf, val;

	buf = kmalloc(CMD_SIZE, GFP_KERNEL);
	if (!buf)
		return -ENOMEM;

	memcpy(buf, &cmd_misc, CMD_SIZE);
	buf[20] = req_a;
	buf[21] = req_b;
	buf[22] = arg_a;
	buf[23] = arg_b;
	buf[24] = arg_c;
	buf[25] = arg_d;

	/* Send request */
	ret = usb_bulk_msg(gm12u320->udev,
			   usb_sndbulkpipe(gm12u320->udev, MISC_SND_EPT),
			   buf, CMD_SIZE, &len, CMD_TIMEOUT);
	if (ret || len != CMD_SIZE) {
		dev_err(&gm12u320->udev->dev, "Misc. req. error %d\n", ret);
		ret = -EIO;
		goto leave;
	}

	/* Read value */
	ret = usb_bulk_msg(gm12u320->udev,
			   usb_rcvbulkpipe(gm12u320->udev, MISC_RCV_EPT),
			   buf, MISC_VALUE_SIZE, &len, DATA_TIMEOUT);
	if (ret || len != MISC_VALUE_SIZE) {
		dev_err(&gm12u320->udev->dev, "Misc. value error %d\n", ret);
		ret = -EIO;
		goto leave;
	}
	val = buf[0];

	/* Read status */
	ret = usb_bulk_msg(gm12u320->udev,
			   usb_rcvbulkpipe(gm12u320->udev, MISC_RCV_EPT),
			   buf, READ_STATUS_SIZE, &len, CMD_TIMEOUT);
	if (ret || len != READ_STATUS_SIZE) {
		dev_err(&gm12u320->udev->dev, "Misc. status error %d\n", ret);
		ret = -EIO;
		goto leave;
	}

	ret = val;
leave:
	kfree(buf);
	return ret;
}

void gm12u320_32bpp_to_24bpp_packed(u8 *dst, u8 *src, int len)
{
	while (len--) {
		*dst++ = *src++;
		*dst++ = *src++;
		*dst++ = *src++;
		src++;
	}
}



static int gm12u320_fb_update_ready(struct gm12u320_device *gm12u320)
{
	int ret;

	mutex_lock(&gm12u320->fb_update.lock);
	ret = !gm12u320->fb_update.run || gm12u320->fb_update.fb != NULL;
	mutex_unlock(&gm12u320->fb_update.lock);

	return ret;
}

static void gm12u320_fb_update_work(struct work_struct *work)
{
	struct gm12u320_device *gm12u320 =
		container_of(work, struct gm12u320_device, fb_update.work);
	int draw_status_timeout = FIRST_FRAME_TIMEOUT;
	int block, block_size, len, x1, x2, y1, y2;
	struct gm12u320_framebuffer *fb;
	int frame = 0;
	int ret = 0;

	printk(KERN_INFO "gm12u320: Workqueue started, gm12u320=%p\n", gm12u320);
	
	/* Check for NULL pointers */
	if (!gm12u320) {
		printk(KERN_ERR "gm12u320: NULL gm12u320 device\n");
		return;
	}
	
	if (!gm12u320->udev) {
		printk(KERN_ERR "gm12u320: NULL udev\n");
		return;
	}
	
	if (!gm12u320->cmd_buf) {
		printk(KERN_ERR "gm12u320: NULL cmd_buf\n");
		return;
	}
	
	/* Check if any data_buf entry is NULL */
	for (int i = 0; i < GM12U320_BLOCK_COUNT; i++) {
		if (!gm12u320->data_buf[i]) {
			printk(KERN_ERR "gm12u320: NULL data_buf[%d]\n", i);
			return;
		}
	}

	while (gm12u320->fb_update.run) {
		printk(KERN_INFO "gm12u320: Workqueue loop iteration, frame=%d\n", frame);
		
		mutex_lock(&gm12u320->fb_update.lock);
		fb = gm12u320->fb_update.fb;
		x1 = gm12u320->fb_update.x1;
		x2 = gm12u320->fb_update.x2;
		y1 = gm12u320->fb_update.y1;
		y2 = gm12u320->fb_update.y2;
		gm12u320->fb_update.fb = NULL;
		mutex_unlock(&gm12u320->fb_update.lock);

		printk(KERN_INFO "gm12u320: fb=%p, x1=%d, x2=%d, y1=%d, y2=%d\n", fb, x1, x2, y1, y2);

		if (fb) {
			printk(KERN_INFO "gm12u320: Processing framebuffer\n");
			gm12u320_fb_mark_dirty(fb, 0, GM12U320_USER_WIDTH, 0, GM12U320_HEIGHT);
		} else {
			printk(KERN_INFO "gm12u320: No framebuffer to process, sending test pattern\n");
			/* Fill data buffers with a simple test pattern */
			for (int i = 0; i < GM12U320_BLOCK_COUNT; i++) {
				int block_size = (i == GM12U320_BLOCK_COUNT - 1) ? 
					DATA_LAST_BLOCK_SIZE : DATA_BLOCK_SIZE;
				/* Fill with a simple pattern: alternating colors */
				for (int j = DATA_BLOCK_HEADER_SIZE; j < block_size - DATA_BLOCK_FOOTER_SIZE; j += 3) {
					gm12u320->data_buf[i][j] = (frame ? 0xFF : 0x00);     /* Red */
					gm12u320->data_buf[i][j+1] = (frame ? 0x00 : 0xFF);   /* Green */
					gm12u320->data_buf[i][j+2] = (frame ? 0x00 : 0x00);   /* Blue */
				}
			}
		}

		for (block = 0; block < GM12U320_BLOCK_COUNT; block++) {
			if (block == GM12U320_BLOCK_COUNT - 1)
				block_size = DATA_LAST_BLOCK_SIZE;
			else
				block_size = DATA_BLOCK_SIZE;

			/* Send data command to device */
			memcpy(gm12u320->cmd_buf, cmd_data, CMD_SIZE);
			gm12u320->cmd_buf[8] = block_size & 0xff;
			gm12u320->cmd_buf[9] = block_size >> 8;
			gm12u320->cmd_buf[20] = 0xfc - block * 4;
			gm12u320->cmd_buf[21] = block | (frame << 7);

			ret = usb_bulk_msg(gm12u320->udev,
				usb_sndbulkpipe(gm12u320->udev, DATA_SND_EPT),
				gm12u320->cmd_buf, CMD_SIZE, &len,
				CMD_TIMEOUT);
			if (ret || len != CMD_SIZE)
				goto err;

			/* Send data block to device */
			ret = usb_bulk_msg(gm12u320->udev,
				usb_sndbulkpipe(gm12u320->udev, DATA_SND_EPT),
				gm12u320->data_buf[block], block_size,
				&len, DATA_TIMEOUT);
			if (ret || len != block_size)
				goto err;

			/* Read status */
			ret = usb_bulk_msg(gm12u320->udev,
				usb_rcvbulkpipe(gm12u320->udev, DATA_RCV_EPT),
				gm12u320->cmd_buf, READ_STATUS_SIZE, &len,
				CMD_TIMEOUT);
			if (ret || len != READ_STATUS_SIZE)
				goto err;
		}

		/* Send draw command to device */
		memcpy(gm12u320->cmd_buf, cmd_draw, CMD_SIZE);
		ret = usb_bulk_msg(gm12u320->udev,
			usb_sndbulkpipe(gm12u320->udev, DATA_SND_EPT),
			gm12u320->cmd_buf, CMD_SIZE, &len, CMD_TIMEOUT);
		if (ret || len != CMD_SIZE)
			goto err;

		/* Read status */
		ret = usb_bulk_msg(gm12u320->udev,
			usb_rcvbulkpipe(gm12u320->udev, DATA_RCV_EPT),
			gm12u320->cmd_buf, READ_STATUS_SIZE, &len,
			draw_status_timeout);
		if (ret || len != READ_STATUS_SIZE)
			goto err;

		draw_status_timeout = CMD_TIMEOUT;
		frame = !frame;

		printk(KERN_INFO "gm12u320: Frame %d sent to device, waiting for next update\n", frame);

		/*
		 * We must draw a frame every 2s otherwise the projector
		 * switches back to showing its logo.
		 */
		wait_event_timeout(gm12u320->fb_update.waitq,
				   gm12u320_fb_update_ready(gm12u320),
				   msecs_to_jiffies(IDLE_TIMEOUT));
	}
	return;
err:
	/* Do not log errors caused by module unload or device unplug */
	if (ret != -ECONNRESET && ret != -ESHUTDOWN)
		dev_err(&gm12u320->udev->dev, "Frame update error: %d\n", ret);
}

void gm12u320_start_fb_update(struct drm_device *dev)
{
	struct gm12u320_device *gm12u320 = dev->dev_private;

	printk(KERN_INFO "gm12u320: Starting fb update workqueue\n");
	mutex_lock(&gm12u320->fb_update.lock);
	gm12u320->fb_update.run = true;
	mutex_unlock(&gm12u320->fb_update.lock);

	queue_work(gm12u320->fb_update.workq, &gm12u320->fb_update.work);
}

void gm12u320_stop_fb_update(struct drm_device *dev)
{
	struct gm12u320_device *gm12u320 = dev->dev_private;

	mutex_lock(&gm12u320->fb_update.lock);
	gm12u320->fb_update.run = false;
	mutex_unlock(&gm12u320->fb_update.lock);

	wake_up(&gm12u320->fb_update.waitq);
	cancel_work_sync(&gm12u320->fb_update.work);
	del_timer_sync(&gm12u320->fb_update.timer);

	mutex_lock(&gm12u320->fb_update.lock);
	if (gm12u320->fb_update.fb) {
		gm12u320->fb_update.fb = NULL;
	}
	mutex_unlock(&gm12u320->fb_update.lock);
}

static void gm12u320_fb_update_timer(struct timer_list *t)
{
	struct gm12u320_device *gm12u320 = from_timer(gm12u320, t, fb_update.timer);
	
	printk(KERN_INFO "gm12u320: Timer fired, starting workqueue\n");
	/* Start the framebuffer update workqueue */
	gm12u320_start_fb_update(gm12u320->ddev);
}

int gm12u320_driver_load(struct drm_device *dev, unsigned long flags)
{
	struct usb_device *udev = (void *)flags;
	struct gm12u320_device *gm12u320;
	int ret = -ENOMEM;

	printk(KERN_INFO "gm12u320: driver_load started\n");
	DRM_DEBUG("\n");
	gm12u320 = kzalloc(sizeof(struct gm12u320_device), GFP_KERNEL);
	if (!gm12u320)
		return -ENOMEM;

	gm12u320->udev = udev;
	gm12u320->ddev = dev;
	dev->dev_private = gm12u320;

	mutex_init(&gm12u320->gem_lock);

	INIT_WORK(&gm12u320->fb_update.work, gm12u320_fb_update_work);
	timer_setup(&gm12u320->fb_update.timer, gm12u320_fb_update_timer, 0);
	mutex_init(&gm12u320->fb_update.lock);
	init_waitqueue_head(&gm12u320->fb_update.waitq);

	ret = gm12u320_set_ecomode(dev);
	if (ret)
		goto err;

	gm12u320->fb_update.workq = create_singlethread_workqueue(DRIVER_NAME);
	if (!gm12u320->fb_update.workq) {
		ret = -ENOMEM;
		goto err;
	}

	ret = gm12u320_usb_alloc(gm12u320);
	if (ret)
		goto err_wq;

	DRM_DEBUG("\n");
	printk(KERN_INFO "gm12u320: About to call gm12u320_modeset_init\n");
	ret = gm12u320_modeset_init(dev);
	printk(KERN_INFO "gm12u320: gm12u320_modeset_init returned: %d\n", ret);
	if (ret)
		goto err_usb;

	printk(KERN_INFO "gm12u320: About to call gm12u320_fbdev_init\n");
	ret = gm12u320_fbdev_init(dev);
	printk(KERN_INFO "gm12u320: gm12u320_fbdev_init returned: %d\n", ret);
	if (ret) {
		DRM_ERROR("Failed to initialize fbdev: %d\n", ret);
		goto err_modeset;
	}

	ret = drm_vblank_init(dev, 1);
	if (ret)
		goto err_fb;

	/* Start framebuffer update after a delay to ensure device is ready */
	mod_timer(&gm12u320->fb_update.timer, jiffies + msecs_to_jiffies(1000));

	return 0;

err_fb:
	gm12u320_fbdev_cleanup(dev);
err_modeset:
	gm12u320_modeset_cleanup(dev);
err_usb:
	gm12u320_usb_free(gm12u320);
err_wq:
	destroy_workqueue(gm12u320->fb_update.workq);
err:
	kfree(gm12u320);
	DRM_ERROR("%d\n", ret);
	return ret;
}

void gm12u320_driver_unload(struct drm_device *dev)
{
	struct gm12u320_device *gm12u320 = dev->dev_private;
	// avoid cleaning up twice, as this function is apparently called twice
	if (gm12u320) {
		gm12u320_fbdev_cleanup(dev);
		gm12u320_modeset_cleanup(dev);
		gm12u320_usb_free(gm12u320);
		destroy_workqueue(gm12u320->fb_update.workq);
		kfree(gm12u320);
		dev->dev_private = 0;
	}
}

int gm12u320_set_ecomode(struct drm_device *dev)
{
	struct gm12u320_device *gm12u320 = dev->dev_private;

	return gm12u320_misc_request(gm12u320, MISC_REQ_GET_SET_ECO_A,
				     MISC_REQ_GET_SET_ECO_B, 0x01 /* set */,
				     eco_mode ? 0x01 : 0x00, 0x00, 0x01);
}
