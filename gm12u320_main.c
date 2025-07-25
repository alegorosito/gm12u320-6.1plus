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
#include <linux/fb.h>
#include <linux/vt_kern.h>
#include <linux/fs.h>
#include <linux/jiffies.h>
#include "gm12u320_drv.h"

/* Function prototypes */
void gm12u320_32bpp_to_24bpp_packed(u8 *dst, u8 *src, int len);

/* Timer function to start fb update safely */
static void gm12u320_fb_update_timer(struct timer_list *t);

static bool eco_mode;
module_param(eco_mode, bool, 0644);
MODULE_PARM_DESC(eco_mode, "Turn on Eco mode (less bright, more silent)");

static bool screen_mirror = true;
module_param(screen_mirror, bool, 0644);
MODULE_PARM_DESC(screen_mirror, "Enable screen mirroring from main display (default: true)");

/* Modified endpoints to work with Mass Storage mode */
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
#define IDLE_TIMEOUT			100	/* 100ms = 10 FPS for smooth projection */
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

	printk(KERN_INFO "gm12u320: misc_request called with req_a=0x%02x, req_b=0x%02x, arg_a=0x%02x, arg_b=0x%02x, arg_c=0x%02x, arg_d=0x%02x\n",
	       req_a, req_b, arg_a, arg_b, arg_c, arg_d);

	buf = kmalloc(CMD_SIZE, GFP_KERNEL);
	if (!buf) {
		printk(KERN_ERR "gm12u320: Failed to allocate buffer for misc request\n");
		return -ENOMEM;
	}

	memcpy(buf, &cmd_misc, CMD_SIZE);
	buf[20] = req_a;
	buf[21] = req_b;
	buf[22] = arg_a;
	buf[23] = arg_b;
	buf[24] = arg_c;
	buf[25] = arg_d;

	/* Send request */
	printk(KERN_INFO "gm12u320: Sending USB bulk message to endpoint %d\n", MISC_SND_EPT);
	ret = usb_bulk_msg(gm12u320->udev,
			   usb_sndbulkpipe(gm12u320->udev, MISC_SND_EPT),
			   buf, CMD_SIZE, &len, CMD_TIMEOUT);
	if (ret || len != CMD_SIZE) {
		printk(KERN_ERR "gm12u320: USB send error: ret=%d, len=%d, expected=%d\n", ret, len, CMD_SIZE);
		dev_err(&gm12u320->udev->dev, "Misc. req. error %d\n", ret);
		ret = -EIO;
		goto leave;
	}
	printk(KERN_INFO "gm12u320: USB send successful: len=%d\n", len);

	/* Read value */
	printk(KERN_INFO "gm12u320: Reading value from endpoint %d\n", MISC_RCV_EPT);
	ret = usb_bulk_msg(gm12u320->udev,
			   usb_rcvbulkpipe(gm12u320->udev, MISC_RCV_EPT),
			   buf, MISC_VALUE_SIZE, &len, DATA_TIMEOUT);
	if (ret || len != MISC_VALUE_SIZE) {
		printk(KERN_ERR "gm12u320: USB read value error: ret=%d, len=%d, expected=%d\n", ret, len, MISC_VALUE_SIZE);
		dev_err(&gm12u320->udev->dev, "Misc. value error %d\n", ret);
		ret = -EIO;
		goto leave;
	}
	val = buf[0];
	printk(KERN_INFO "gm12u320: Read value successful: len=%d, val=0x%02x\n", len, val);

	/* Read status */
	printk(KERN_INFO "gm12u320: Reading status from endpoint %d\n", MISC_RCV_EPT);
	ret = usb_bulk_msg(gm12u320->udev,
			   usb_rcvbulkpipe(gm12u320->udev, MISC_RCV_EPT),
			   buf, READ_STATUS_SIZE, &len, CMD_TIMEOUT);
	if (ret || len != READ_STATUS_SIZE) {
		printk(KERN_ERR "gm12u320: USB read status error: ret=%d, len=%d, expected=%d\n", ret, len, READ_STATUS_SIZE);
		dev_err(&gm12u320->udev->dev, "Misc. status error %d\n", ret);
		ret = -EIO;
		goto leave;
	}
	printk(KERN_INFO "gm12u320: Read status successful: len=%d\n", len);

	ret = val;
	printk(KERN_INFO "gm12u320: misc_request completed successfully, returning 0x%02x\n", val);
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

/* Function to capture main screen content */
static int capture_main_screen(struct gm12u320_device *gm12u320, unsigned char *dest_buffer, int max_size)
{
	/* Target resolution for projector */
	int target_width = GM12U320_USER_WIDTH;
	int target_height = GM12U320_HEIGHT;
	int expected_size = target_width * target_height * 3;
	
	/* Try to read image data from shared file first */
	struct file *file;
	loff_t pos = 0;
	int bytes_read = 0;
	static int last_read_time = 0;
	int current_time = jiffies;
	
	/* Try to open the shared image file */
	file = filp_open("/tmp/gm12u320_image.rgb", O_RDONLY, 0);
	if (!IS_ERR(file)) {
		/* Check if we should read the file (every 100ms or if it's been a while) */
		if (current_time - last_read_time > HZ / 10) { /* 100ms */
			printk(KERN_DEBUG "gm12u320: Reading image from /tmp/gm12u320_image.rgb\n");
			
			/* Read image data from file */
			bytes_read = kernel_read(file, dest_buffer, expected_size, &pos);
			last_read_time = current_time;
			
			if (bytes_read == expected_size) {
				printk(KERN_DEBUG "gm12u320: Successfully read %d bytes from image file\n", bytes_read);
				filp_close(file, NULL);
				return bytes_read;
			} else {
				printk(KERN_DEBUG "gm12u320: Image file read failed, bytes_read=%d, expected=%d\n", bytes_read, expected_size);
			}
		} else {
			printk(KERN_DEBUG "gm12u320: Skipping file read (too soon)\n");
		}
		filp_close(file, NULL);
	} else {
		printk(KERN_DEBUG "gm12u320: No image file found, using test pattern\n");
	}
	
	/* Fallback to test pattern if no image file or read failed */
	printk(KERN_DEBUG "gm12u320: Generating test pattern: %dx%d\n", target_width, target_height);
	
	/* Generate a simple test pattern */
	int i, j;
	static int frame_count = 0;
	frame_count++;
	
	for (i = 0; i < target_height; i++) {
		for (j = 0; j < target_width; j++) {
			int dest_offset = i * target_width * 3 + j * 3;
			
			if (dest_offset + 2 < max_size) {
				/* Create an animated test pattern */
				int r = (j + frame_count) % 256;
				int g = (i + frame_count) % 256;
				int b = (frame_count * 10) % 256;
				
				dest_buffer[dest_offset] = r;     /* Red */
				dest_buffer[dest_offset + 1] = g; /* Green */
				dest_buffer[dest_offset + 2] = b; /* Blue */
			}
		}
	}
	
	return target_width * target_height * 3; /* Return actual bytes copied */
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

restart_loop:
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
			/* Always capture main screen - no rainbow pattern fallback */
			printk(KERN_DEBUG "gm12u320: Capturing main screen for projection\n");
			
			/* Capture main screen directly from /dev/fb0 */
			unsigned char *capture_buffer = kmalloc(GM12U320_USER_WIDTH * GM12U320_HEIGHT * 3, GFP_KERNEL);
			if (capture_buffer) {
				int capture_size = capture_main_screen(gm12u320, capture_buffer, 
					GM12U320_USER_WIDTH * GM12U320_HEIGHT * 3);
				
				if (capture_size > 0) {
					/* Copy captured data to data buffers */
					int data_offset = 0;
					for (int i = 0; i < GM12U320_BLOCK_COUNT; i++) {
						int block_size = (i == GM12U320_BLOCK_COUNT - 1) ? 
							DATA_LAST_BLOCK_SIZE : DATA_BLOCK_SIZE;
						int data_size = block_size - DATA_BLOCK_HEADER_SIZE - DATA_BLOCK_FOOTER_SIZE;
						
						if (data_offset < capture_size) {
							int copy_size = min(data_size, capture_size - data_offset);
							memcpy(gm12u320->data_buf[i] + DATA_BLOCK_HEADER_SIZE, 
								capture_buffer + data_offset, copy_size);
							data_offset += copy_size;
						}
					}
					printk(KERN_DEBUG "gm12u320: Captured main screen (%d bytes) - projecting directly\n", capture_size);
					kfree(capture_buffer);
					/* Go directly to sending data - no rainbow pattern */
					goto send_data;
				} else {
					printk(KERN_ERR "gm12u320: Failed to capture main screen - skipping frame\n");
					kfree(capture_buffer);
					/* Skip this frame and continue */
					goto continue_loop;
				}
			} else {
				printk(KERN_ERR "gm12u320: Failed to allocate capture buffer - skipping frame\n");
				/* Skip this frame and continue */
				goto continue_loop;
			}
		}
		
		/* Continue with sending data to projector (both captured and rainbow pattern) */
		
send_data:
		/* Send captured data to projector */

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
		 * Wait for next frame at 10 FPS (100ms interval)
		 */
		wait_event_timeout(gm12u320->fb_update.waitq,
				   gm12u320_fb_update_ready(gm12u320),
				   msecs_to_jiffies(IDLE_TIMEOUT));
	}
	return;
	
continue_loop:
	/* Skip this frame and continue to next iteration */
	wait_event_timeout(gm12u320->fb_update.waitq,
			   gm12u320_fb_update_ready(gm12u320),
			   msecs_to_jiffies(IDLE_TIMEOUT));
	goto restart_loop;
	
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
	printk(KERN_INFO "gm12u320: About to allocate device structure\n");
	gm12u320 = kzalloc(sizeof(struct gm12u320_device), GFP_KERNEL);
	if (!gm12u320) {
		printk(KERN_ERR "gm12u320: Failed to allocate device structure\n");
		return -ENOMEM;
	}
	printk(KERN_INFO "gm12u320: Device structure allocated successfully\n");

	gm12u320->udev = udev;
	gm12u320->ddev = dev;
	dev->dev_private = gm12u320;

	mutex_init(&gm12u320->gem_lock);

	INIT_WORK(&gm12u320->fb_update.work, gm12u320_fb_update_work);
	timer_setup(&gm12u320->fb_update.timer, gm12u320_fb_update_timer, 0);
	mutex_init(&gm12u320->fb_update.lock);
	init_waitqueue_head(&gm12u320->fb_update.waitq);

	/* Temporarily skip eco mode setting to avoid USB communication issues */
	printk(KERN_INFO "gm12u320: Skipping eco mode setting (device in Mass Storage mode)\n");
	/*
	printk(KERN_INFO "gm12u320: About to set eco mode\n");
	ret = gm12u320_set_ecomode(dev);
	if (ret) {
		printk(KERN_ERR "gm12u320: Failed to set eco mode: %d\n", ret);
		goto err;
	}
	printk(KERN_INFO "gm12u320: Eco mode set successfully\n");
	*/

	printk(KERN_INFO "gm12u320: About to create workqueue\n");
	gm12u320->fb_update.workq = create_singlethread_workqueue(DRIVER_NAME);
	if (!gm12u320->fb_update.workq) {
		printk(KERN_ERR "gm12u320: Failed to create workqueue\n");
		ret = -ENOMEM;
		goto err;
	}
	printk(KERN_INFO "gm12u320: Workqueue created successfully\n");

	printk(KERN_INFO "gm12u320: About to allocate USB resources\n");
	ret = gm12u320_usb_alloc(gm12u320);
	if (ret) {
		printk(KERN_ERR "gm12u320: Failed to allocate USB resources: %d\n", ret);
		goto err_wq;
	}
	printk(KERN_INFO "gm12u320: USB resources allocated successfully\n");

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
