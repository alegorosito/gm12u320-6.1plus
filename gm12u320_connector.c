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
#include <drm/drm_crtc.h>
#include <drm/drm_edid.h>
#include <drm/drm_crtc_helper.h>
#include <drm/drm_connector.h>
#include <drm/drm_atomic_helper.h>
#include "gm12u320_drv.h"



static int gm12u320_connector_get_modes(struct drm_connector *connector)
{
	struct drm_display_mode *mode;

	mode = drm_mode_duplicate(connector->dev, &(struct drm_display_mode){
		DRM_MODE("1280x720", DRM_MODE_TYPE_DRIVER, 74250, 1280, 1390,
			 1430, 1650, 0, 720, 725, 730, 750, 0,
			 DRM_MODE_FLAG_PHSYNC | DRM_MODE_FLAG_PVSYNC)
	});

	if (!mode)
		return 0;

	drm_mode_probed_add(connector, mode);

	return 1;
}

static enum drm_connector_status
gm12u320_detect(struct drm_connector *connector, bool force)
{
	return connector_status_connected;
}

static int gm12u320_connector_set_property(struct drm_connector *connector,
					   struct drm_property *property,
					   uint64_t val)
{
	return 0;
}

static void gm12u320_connector_destroy(struct drm_connector *connector)
{
	drm_connector_unregister(connector);
	drm_connector_cleanup(connector);
	kfree(connector);
}

static const struct drm_connector_funcs gm12u320_connector_funcs = {
	.detect = gm12u320_detect,
	.get_modes = gm12u320_connector_get_modes,
	.destroy = gm12u320_connector_destroy,
	.set_property = gm12u320_connector_set_property,
	.reset = drm_atomic_helper_connector_reset,
	.atomic_duplicate_state = drm_atomic_helper_connector_duplicate_state,
	.atomic_destroy_state = drm_atomic_helper_connector_destroy_state,
};

int gm12u320_connector_init(struct drm_device *dev,
			    struct drm_encoder *encoder)
{
	struct drm_connector *connector;

	connector = kzalloc(sizeof(struct drm_connector), GFP_KERNEL);
	if (!connector)
		return -ENOMEM;

	drm_connector_init(dev, connector, &gm12u320_connector_funcs,
			   DRM_MODE_CONNECTOR_Unknown);

	drm_connector_register(connector);
	drm_connector_attach_encoder(connector, encoder);

	return 0;
}
