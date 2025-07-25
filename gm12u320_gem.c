/*
 * Copyright (C) 2012-2016 Red Hat Inc.
 *
 * This file is subject to the terms and conditions of the GNU General Public
 * License v2. See the file COPYING in the main directory of this archive for
 * more details.
 */

#include <linux/kernel.h>
#include <linux/shmem_fs.h>
#include <linux/dma-buf.h>
#include <drm/drm_gem.h>
#include <drm/drm_gem_shmem_helper.h>
#include <drm/drm_print.h>
#include "gm12u320_drv.h"

struct gm12u320_gem_object *
gm12u320_gem_alloc_object(struct drm_device *dev, size_t size)
{
	struct gm12u320_gem_object *obj;

	obj = kzalloc(sizeof(*obj), GFP_KERNEL);
	if (obj == NULL)
		return NULL;

	if (drm_gem_object_init(dev, &obj->base, size) != 0) {
		kfree(obj);
		return NULL;
	}

	obj->flags = GM12U320_BO_CACHEABLE;
	return obj;
}

static int gm12u320_gem_create(struct drm_file *file, struct drm_device *dev,
			       uint64_t size, uint32_t *handle_p)
{
	struct gm12u320_gem_object *obj;
	int ret;
	u32 handle;

	size = roundup(size, PAGE_SIZE);

	obj = gm12u320_gem_alloc_object(dev, size);
	if (obj == NULL)
		return -ENOMEM;

	ret = drm_gem_handle_create(file, &obj->base, &handle);
	if (ret) {
		drm_gem_object_release(&obj->base);
		kfree(obj);
		return ret;
	}

	drm_gem_object_put(&obj->base);
	*handle_p = handle;
	return 0;
}

static void update_vm_cache_attr(struct gm12u320_gem_object *obj,
				 struct vm_area_struct *vma)
{
	DRM_DEBUG_KMS("flags = 0x%x\n", obj->flags);

	/* non-cacheable as default. */
	if (obj->flags & GM12U320_BO_CACHEABLE) {
		vma->vm_page_prot = vm_get_page_prot(vma->vm_flags);
	} else if (obj->flags & GM12U320_BO_WC) {
		vma->vm_page_prot =
			pgprot_writecombine(vm_get_page_prot(vma->vm_flags));
	} else {
		vma->vm_page_prot =
			pgprot_noncached(vm_get_page_prot(vma->vm_flags));
	}
}

int gm12u320_dumb_create(struct drm_file *file, struct drm_device *dev,
			 struct drm_mode_create_dumb *args)
{
	args->pitch = args->width * DIV_ROUND_UP(args->bpp, 8);
	args->size = args->pitch * args->height;
	return gm12u320_gem_create(file, dev,
			      args->size, &args->handle);
}

int gm12u320_drm_gem_mmap(struct file *filp, struct vm_area_struct *vma)
{
	int ret;

	ret = drm_gem_mmap(filp, vma);
	if (ret)
		return ret;

	vm_flags_set(vma, VM_MIXEDMAP);
	vm_flags_clear(vma, VM_PFNMAP);

	update_vm_cache_attr(to_gm12u320_bo(vma->vm_private_data), vma);

	return ret;
}

vm_fault_t gm12u320_gem_fault(struct vm_fault *vmf)
{
	struct vm_area_struct *vma = vmf->vma;
	struct gm12u320_gem_object *obj = to_gm12u320_bo(vma->vm_private_data);
	unsigned int page_offset;
	struct page *page;
	int ret = 0;

	page_offset = (vmf->address - vma->vm_start) >> PAGE_SHIFT;

	if (!obj->pages)
		return VM_FAULT_SIGBUS;

	page = obj->pages[page_offset];
	ret = vm_insert_page(vma, vmf->address, page);
	switch (ret) {
	case -EAGAIN:
	case 0:
	case -ERESTARTSYS:
		return VM_FAULT_NOPAGE;
	case -ENOMEM:
		return VM_FAULT_OOM;
	default:
		return VM_FAULT_SIGBUS;
	}
}

int gm12u320_gem_get_pages(struct gm12u320_gem_object *obj)
{
	struct page **pages;
	int page_count = obj->base.size / PAGE_SIZE;
	int i;

	printk(KERN_INFO "gm12u320: gem_get_pages: Starting, size=%zu, page_count=%d\n", obj->base.size, page_count);

	if (obj->pages) {
		printk(KERN_INFO "gm12u320: gem_get_pages: Pages already exist\n");
		return 0;
	}

	/* Allocate pages array */
	printk(KERN_INFO "gm12u320: gem_get_pages: Allocating pages array\n");
	pages = kvmalloc_array(page_count, sizeof(struct page *), GFP_KERNEL);
	if (!pages) {
		printk(KERN_ERR "gm12u320: gem_get_pages: Failed to allocate pages array\n");
		return -ENOMEM;
	}

	/* Allocate actual pages */
	printk(KERN_INFO "gm12u320: gem_get_pages: Allocating %d pages\n", page_count);
	for (i = 0; i < page_count; i++) {
		pages[i] = alloc_page(GFP_KERNEL);
		if (!pages[i]) {
			printk(KERN_ERR "gm12u320: gem_get_pages: Failed to allocate page %d\n", i);
			/* Clean up already allocated pages */
			while (--i >= 0) {
				__free_page(pages[i]);
			}
			kvfree(pages);
			return -ENOMEM;
		}
	}

	obj->pages = pages;
	printk(KERN_INFO "gm12u320: gem_get_pages: Success, allocated %d pages\n", page_count);
	return 0;
}

void gm12u320_gem_put_pages(struct gm12u320_gem_object *obj)
{
	if (obj->base.import_attach) {
		kvfree(obj->pages);
		obj->pages = NULL;
		return;
	}

	kvfree(obj->pages);
	obj->pages = NULL;
}

int gm12u320_gem_vmap(struct gm12u320_gem_object *obj)
{
	int page_count = obj->base.size / PAGE_SIZE;
	int ret;
	struct iosys_map map;

	printk(KERN_INFO "gm12u320: gem_vmap: Starting, size=%zu, page_count=%d\n", obj->base.size, page_count);

	if (obj->base.import_attach) {
		printk(KERN_INFO "gm12u320: gem_vmap: Using import_attach\n");
		ret = dma_buf_vmap(obj->base.import_attach->dmabuf, &map);
		if (ret) {
			printk(KERN_ERR "gm12u320: gem_vmap: dma_buf_vmap failed: %d\n", ret);
			return ret;
		}
		obj->vmapping = map.vaddr;
		printk(KERN_INFO "gm12u320: gem_vmap: dma_buf_vmap success\n");
		return 0;
	}

	printk(KERN_INFO "gm12u320: gem_vmap: Getting pages\n");
	ret = gm12u320_gem_get_pages(obj);
	if (ret) {
		printk(KERN_ERR "gm12u320: gem_vmap: get_pages failed: %d\n", ret);
		return ret;
	}

	printk(KERN_INFO "gm12u320: gem_vmap: Calling vmap\n");
	obj->vmapping = vmap(obj->pages, page_count, 0, PAGE_KERNEL);
	if (!obj->vmapping) {
		printk(KERN_ERR "gm12u320: gem_vmap: vmap failed\n");
		return -ENOMEM;
	}
	
	printk(KERN_INFO "gm12u320: gem_vmap: Success, vmapping=%p\n", obj->vmapping);
	return 0;
}

void gm12u320_gem_vunmap(struct gm12u320_gem_object *obj)
{
	struct iosys_map map;

	if (obj->base.import_attach) {
		iosys_map_set_vaddr(&map, obj->vmapping);
		dma_buf_vunmap(obj->base.import_attach->dmabuf, &map);
		return;
	}

	vunmap(obj->vmapping);

	gm12u320_gem_put_pages(obj);
}

void gm12u320_gem_free_object(struct drm_gem_object *gem_obj)
{
	struct gm12u320_gem_object *obj = to_gm12u320_bo(gem_obj);

	if (obj->vmapping)
		gm12u320_gem_vunmap(obj);

	if (gem_obj->import_attach) {
		drm_prime_gem_destroy(gem_obj, obj->sg);
	}

	if (obj->pages)
		gm12u320_gem_put_pages(obj);

	drm_gem_free_mmap_offset(gem_obj);
}

/* the dumb interface doesn't work with the GEM straight MMAP
   interface, it expects to do MMAP on the drm fd, like normal */
int gm12u320_gem_mmap(struct drm_file *file, struct drm_device *dev,
		      uint32_t handle, uint64_t *offset)
{
	struct gm12u320_gem_object *gobj;
	struct drm_gem_object *obj;
	int ret = 0;

	obj = drm_gem_object_lookup(file, handle);
	if (obj == NULL) {
		return -ENOENT;
	}
	gobj = to_gm12u320_bo(obj);

	ret = gm12u320_gem_get_pages(gobj);
	if (ret)
		goto out;
	ret = drm_gem_create_mmap_offset(obj);
	if (ret)
		goto out;

	*offset = drm_vma_node_offset_addr(&gobj->base.vma_node);

out:
	drm_gem_object_put(&gobj->base);
	return ret;
}
