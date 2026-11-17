/*
 * Copyright (c) 2026 Keyboardio Preonic Custom Firmware
 * SPDX-License-Identifier: MIT
 */

#define DT_DRV_COMPAT zmk_behavior_preonic_fn

#include <zephyr/device.h>
#include <zephyr/logging/log.h>
#include <drivers/behavior.h>
#include <zmk/behavior.h>
#include <dt-bindings/zmk/preonic_fn.h>

#include "battery_typer.h"
#include "butterfly_status.h"
#include "dynamic_macro.h"
#include "password_generator.h"
#if IS_ENABLED(CONFIG_KEYBOARDIO_PREONIC_SOUND)
#include "preonic_sound.h"
#endif

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

static int on_keymap_binding_pressed(struct zmk_behavior_binding *binding,
                                     struct zmk_behavior_binding_event event) {
    ARG_UNUSED(event);

    switch (binding->param1) {
    case PREONIC_FN_MACRO_REC_1:
        dynamic_macro_record_toggle(1);
        break;
    case PREONIC_FN_MACRO_PLAY_1:
        dynamic_macro_play(1);
        break;
    case PREONIC_FN_MACRO_REC_2:
        dynamic_macro_record_toggle(2);
        break;
    case PREONIC_FN_MACRO_PLAY_2:
        dynamic_macro_play(2);
        break;
    case PREONIC_FN_MACRO_REC_3:
        dynamic_macro_record_toggle(3);
        break;
    case PREONIC_FN_MACRO_PLAY_3:
        dynamic_macro_play(3);
        break;
    case PREONIC_FN_PW_DB_SAFE:
        password_generator_trigger(PW_MODE_DB_SAFE);
        break;
    case PREONIC_FN_PW_WEB_EXT:
        password_generator_trigger(PW_MODE_WEB_EXTENDED);
        break;
    case PREONIC_FN_PW_ALPHA:
        password_generator_trigger(PW_MODE_ALPHANUMERIC);
        break;
#if IS_ENABLED(CONFIG_KEYBOARDIO_PREONIC_SOUND)
    case PREONIC_FN_SOUND_MASTER:
        preonic_sound_toggle_master();
        break;
    case PREONIC_FN_SOUND_CLICKY:
        preonic_sound_toggle_clicky();
        break;
#endif
    case PREONIC_FN_BATT_GAUGE:
        butterfly_show_battery();
        break;
    case PREONIC_FN_BATT_TYPE:
        preonic_type_battery_status();
        break;
    default:
        LOG_WRN("Unknown preonic_fn action: 0x%x", binding->param1);
        return ZMK_BEHAVIOR_OPAQUE;
    }

    return ZMK_BEHAVIOR_OPAQUE;
}

static int on_keymap_binding_released(struct zmk_behavior_binding *binding,
                                      struct zmk_behavior_binding_event event) {
    ARG_UNUSED(event);

    if (binding->param1 == PREONIC_FN_BATT_GAUGE) {
        butterfly_hide_battery();
    }

    return ZMK_BEHAVIOR_OPAQUE;
}

static const struct behavior_driver_api behavior_preonic_fn_driver_api = {
    .binding_pressed = on_keymap_binding_pressed,
    .binding_released = on_keymap_binding_released,
    .locality = BEHAVIOR_LOCALITY_CENTRAL,
};

#define PREONIC_FN_INST(n)                                                                         \
    BEHAVIOR_DT_INST_DEFINE(n, NULL, NULL, NULL, NULL, POST_KERNEL,                                \
                            CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &behavior_preonic_fn_driver_api);

DT_INST_FOREACH_STATUS_OKAY(PREONIC_FN_INST)
