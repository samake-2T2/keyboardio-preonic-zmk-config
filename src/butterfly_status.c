/*
 * Copyright (c) 2026 Keyboardio Preonic Custom Firmware
 * SPDX-License-Identifier: MIT
 */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/led_strip.h>
#include <zephyr/init.h>
#include <zephyr/logging/log.h>

#if defined(CONFIG_SOC_FAMILY_NRF) || defined(NRF52840_XXAA) || defined(NRF_POWER)
#include <helpers/nrfx_reset_reason.h>
#include <hal/nrf_power.h>
#endif

#include <zmk/activity.h>
#include <zmk/battery.h>
#include <zmk/ble.h>
#include <zmk/endpoints.h>
#include <zmk/usb.h>
#include <zmk/event_manager.h>
#include <zmk/events/activity_state_changed.h>
#include <zmk/events/battery_state_changed.h>
#include <zmk/events/ble_active_profile_changed.h>
#include <zmk/events/endpoint_changed.h>
#include <zmk/events/usb_conn_state_changed.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/keymap.h>

#include "butterfly_status.h"
#include "battery_typer.h"
#if IS_ENABLED(CONFIG_KEYBOARDIO_PREONIC_SOUND)
#include "preonic_sound.h"
#endif

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#if DT_NODE_HAS_PROP(DT_CHOSEN(zmk_butterfly), chain_length)
#define BUTTERFLY_NODE DT_CHOSEN(zmk_butterfly)
#elif DT_NODE_HAS_PROP(DT_CHOSEN(zmk_underglow), chain_length)
#define BUTTERFLY_NODE DT_CHOSEN(zmk_underglow)
#elif DT_NODE_EXISTS(DT_NODELABEL(led_strip))
#define BUTTERFLY_NODE DT_NODELABEL(led_strip)
#else
#error "Butterfly LED strip node not found in devicetree"
#endif

#define BUTTERFLY_NUM_LEDS DT_PROP(BUTTERFLY_NODE, chain_length)

#ifndef CONFIG_BUTTERFLY_BOOT_ANIM_MS
#define CONFIG_BUTTERFLY_BOOT_ANIM_MS 1600
#endif

#define BOOT_ANIM_FRAME_MS 20

#define FN_LAYER_INDEX 3
#define TRI_LAYER_INDEX 4
#define B_KEY_POSITION 44
#define P_KEY_POSITION 25

static const struct device *const strip_dev = DEVICE_DT_GET(BUTTERFLY_NODE);

static struct k_work_delayable butterfly_work;
static struct k_work_delayable boot_endpoint_work;
static int64_t state_change_time = 0;
static int64_t boot_start_time = 0;
static bool boot_anim_done = false;
static bool blink_state = false;
static enum zmk_activity_state current_activity = ZMK_ACTIVITY_ACTIVE;

static bool is_battery_gauge = false;
static bool low_battery_warned = false;

static enum butterfly_macro_mode current_macro_mode = BUTTERFLY_MACRO_IDLE;
static int64_t macro_anim_start_time = 0;
static int64_t macro_play_end_time = 0;

static uint8_t pw_gauge_wings = 0;
static int64_t pw_gauge_end_time = 0;
static bool pw_success_anim = false;
static int64_t pw_success_end_time = 0;

static inline struct led_rgb make_rgb(uint8_t r, uint8_t g, uint8_t b) {
    return (struct led_rgb){ .r = r, .g = g, .b = b };
}

static void update_leds(struct led_rgb *pixels) {
    if (!device_is_ready(strip_dev)) {
        return;
    }
    (void)led_strip_update_rgb(strip_dev, pixels, BUTTERFLY_NUM_LEDS);
}

static void set_all_off(void) {
    struct led_rgb pixels[BUTTERFLY_NUM_LEDS];
    for (size_t i = 0; i < BUTTERFLY_NUM_LEDS; i++) {
        pixels[i] = make_rgb(0, 0, 0);
    }
    update_leds(pixels);
}

static void butterfly_work_handler(struct k_work *work) {
    if (current_activity == ZMK_ACTIVITY_SLEEP) {
        boot_anim_done = true;
        is_battery_gauge = false;
        set_all_off();
        return;
    }

#if CONFIG_BUTTERFLY_BOOT_ANIM_MS > 0
    if (!boot_anim_done) {
        int64_t elapsed = k_uptime_get() - boot_start_time;
        if (elapsed < CONFIG_BUTTERFLY_BOOT_ANIM_MS) {
            int64_t x = (elapsed * 1000) / CONFIG_BUTTERFLY_BOOT_ANIM_MS;
            if (x < 0) {
                x = 0;
            } else if (x > 1000) {
                x = 1000;
            }
            uint32_t bell = (uint32_t)((4 * x * (1000 - x)) / 1000);
            uint32_t eased = (bell * bell) / 1000;
            uint8_t peak = (uint8_t)CONFIG_BUTTERFLY_BRIGHTNESS;
            uint8_t brt = (uint8_t)(((uint32_t)peak * eased) / 1000);
            uint8_t r = brt;
            uint8_t g = (uint8_t)(((uint16_t)brt * 35 + 50) / 100);
            uint8_t b = 0;

            struct led_rgb pixels[BUTTERFLY_NUM_LEDS];
            for (size_t i = 0; i < BUTTERFLY_NUM_LEDS; i++) {
                pixels[i] = make_rgb(r, g, b);
            }
            update_leds(pixels);

            k_work_reschedule(&butterfly_work, K_MSEC(BOOT_ANIM_FRAME_MS));
            return;
        }

        boot_anim_done = true;
        state_change_time = k_uptime_get();
    }
#endif

    if (current_macro_mode == BUTTERFLY_MACRO_PLAY_1 || current_macro_mode == BUTTERFLY_MACRO_PLAY_2 || current_macro_mode == BUTTERFLY_MACRO_PLAY_3) {
        if (k_uptime_get() >= macro_play_end_time) {
            current_macro_mode = BUTTERFLY_MACRO_IDLE;
            state_change_time = k_uptime_get();
        } else {
            uint8_t brt = (uint8_t)CONFIG_BUTTERFLY_BRIGHTNESS;
            struct led_rgb pixels[BUTTERFLY_NUM_LEDS];
            for (size_t i = 0; i < BUTTERFLY_NUM_LEDS; i++) {
                if (current_macro_mode == BUTTERFLY_MACRO_PLAY_1) {
                    pixels[i] = make_rgb(brt, 0, 0); // Solid Red flash
                } else if (current_macro_mode == BUTTERFLY_MACRO_PLAY_2) {
                    pixels[i] = make_rgb(brt, 0, brt); // Solid Purple flash
                } else {
                    pixels[i] = make_rgb(brt, (uint8_t)(((uint16_t)brt * 60) / 100), 0); // Solid Amber/Gold flash
                }
            }
            update_leds(pixels);
            int64_t rem = macro_play_end_time - k_uptime_get();
            k_work_reschedule(&butterfly_work, K_MSEC(rem > 0 ? rem : 1));
            return;
        }
    }

    if (current_macro_mode == BUTTERFLY_MACRO_REC_1 || current_macro_mode == BUTTERFLY_MACRO_REC_2 || current_macro_mode == BUTTERFLY_MACRO_REC_3) {
        int64_t elapsed = (k_uptime_get() - macro_anim_start_time) % 1400;
        uint32_t phase = (elapsed < 700) ? (uint32_t)elapsed : (uint32_t)(1400 - elapsed);
        uint8_t max_b = (uint8_t)CONFIG_BUTTERFLY_BRIGHTNESS;
        uint8_t min_b = 20;
        uint8_t brt = min_b + (uint8_t)(((uint32_t)(max_b - min_b) * phase) / 700);

        struct led_rgb pixels[BUTTERFLY_NUM_LEDS];
        for (size_t i = 0; i < BUTTERFLY_NUM_LEDS; i++) {
            if (current_macro_mode == BUTTERFLY_MACRO_REC_1) {
                pixels[i] = make_rgb(brt, 0, 0); // Red breathing pulse
            } else if (current_macro_mode == BUTTERFLY_MACRO_REC_2) {
                pixels[i] = make_rgb(brt, 0, brt); // Purple breathing pulse
            } else {
                pixels[i] = make_rgb(brt, (uint8_t)(((uint16_t)brt * 60) / 100), 0); // Amber/Gold breathing pulse
            }
        }
        update_leds(pixels);
        k_work_reschedule(&butterfly_work, K_MSEC(25));
        return;
    }

    if (pw_success_anim) {
        if (k_uptime_get() >= pw_success_end_time) {
            pw_success_anim = false;
            state_change_time = k_uptime_get();
        } else {
            uint8_t brt = (uint8_t)CONFIG_BUTTERFLY_BRIGHTNESS;
            struct led_rgb pixels[BUTTERFLY_NUM_LEDS];
            for (size_t i = 0; i < BUTTERFLY_NUM_LEDS; i++) {
                pixels[i] = make_rgb(brt, (uint8_t)(((uint16_t)brt * 85) / 100), 0);
            }
            update_leds(pixels);
            int64_t rem = pw_success_end_time - k_uptime_get();
            k_work_reschedule(&butterfly_work, K_MSEC(rem > 0 ? rem : 1));
            return;
        }
    }

    if (pw_gauge_wings > 0) {
        if (k_uptime_get() >= pw_gauge_end_time) {
            pw_gauge_wings = 0;
            state_change_time = k_uptime_get();
        } else {
            uint8_t brt = (uint8_t)CONFIG_BUTTERFLY_BRIGHTNESS;
            struct led_rgb pixels[BUTTERFLY_NUM_LEDS];
            for (size_t i = 0; i < BUTTERFLY_NUM_LEDS; i++) {
                pixels[i] = make_rgb(0, 0, 0);
            }
            for (size_t i = 0; i < pw_gauge_wings && i < BUTTERFLY_NUM_LEDS; i++) {
                pixels[i] = make_rgb(brt, (uint8_t)(((uint16_t)brt * 60) / 100), 0);
            }
            update_leds(pixels);
            int64_t rem = pw_gauge_end_time - k_uptime_get();
            k_work_reschedule(&butterfly_work, K_MSEC(rem > 0 ? rem : 1));
            return;
        }
    }

    if (is_battery_gauge) {
        uint8_t soc = zmk_battery_state_of_charge();
        uint8_t brt = (uint8_t)CONFIG_BUTTERFLY_BRIGHTNESS;
        struct led_rgb pixels[BUTTERFLY_NUM_LEDS];
        for (size_t i = 0; i < BUTTERFLY_NUM_LEDS; i++) {
            pixels[i] = make_rgb(0, 0, 0);
        }

        if (soc >= 75) {
            // 4 wings green
            for (size_t i = 0; i < 4 && i < BUTTERFLY_NUM_LEDS; i++) {
                pixels[i] = make_rgb(0, brt, 0);
            }
        } else if (soc >= 50) {
            // 3 wings lime green
            for (size_t i = 0; i < 3 && i < BUTTERFLY_NUM_LEDS; i++) {
                pixels[i] = make_rgb((uint8_t)(((uint16_t)brt * 40) / 100), brt, 0);
            }
        } else if (soc >= 25) {
            // 2 wings orange
            for (size_t i = 0; i < 2 && i < BUTTERFLY_NUM_LEDS; i++) {
                pixels[i] = make_rgb(brt, (uint8_t)(((uint16_t)brt * 30) / 100), 0);
            }
        } else {
            // 1 wing red
            if (BUTTERFLY_NUM_LEDS > 0) {
                pixels[0] = make_rgb(brt, 0, 0);
            }
        }
        update_leds(pixels);
        return;
    }

    struct led_rgb pixels[BUTTERFLY_NUM_LEDS];
    for (size_t i = 0; i < BUTTERFLY_NUM_LEDS; i++) {
        pixels[i] = make_rgb(0, 0, 0);
    }

    enum zmk_transport pref = zmk_endpoint_get_preferred_transport();
    struct zmk_endpoint_instance endpoint = zmk_endpoint_get_selected();

    bool is_usb = false;
#if IS_ENABLED(CONFIG_ZMK_USB)
    // USB output is active if preferred transport is not forced to BLE,
    // and either selected transport is USB or USB HID is ready to communicate
    if (pref != ZMK_TRANSPORT_BLE &&
        (endpoint.transport == ZMK_TRANSPORT_USB || zmk_usb_is_hid_ready())) {
        is_usb = true;
    }
#endif

    if (is_usb) {
#if IS_ENABLED(CONFIG_ZMK_USB)
        int64_t elapsed = k_uptime_get() - state_change_time;
        bool is_dimmed = (CONFIG_BUTTERFLY_TIMEOUT_MS > 0 && elapsed >= CONFIG_BUTTERFLY_TIMEOUT_MS);
        uint8_t brt = is_dimmed ? (uint8_t)CONFIG_BUTTERFLY_DIM_BRIGHTNESS : (uint8_t)CONFIG_BUTTERFLY_BRIGHTNESS;

#if defined(CONFIG_BUTTERFLY_USB_COLOR_PURPLE)
        struct led_rgb usb_color = make_rgb((uint8_t)(((uint16_t)brt * 80) / 100), 0, brt);
#elif defined(CONFIG_BUTTERFLY_USB_COLOR_CYAN)
        struct led_rgb usb_color = make_rgb(0, brt, brt);
#else
        // Clean White by default to avoid overlapping with battery gauge (Green/Lime/Orange/Red)
        struct led_rgb usb_color = make_rgb(brt, brt, brt);
#endif

        for (size_t i = 0; i < BUTTERFLY_NUM_LEDS; i++) {
            pixels[i] = usb_color;
        }
        update_leds(pixels);

        if (!is_dimmed && CONFIG_BUTTERFLY_TIMEOUT_MS > 0) {
            int64_t remaining = CONFIG_BUTTERFLY_TIMEOUT_MS - elapsed;
            if (remaining > 0) {
                k_work_reschedule(&butterfly_work, K_MSEC(remaining + 10));
            }
        }
        return;
#endif
    }

#if IS_ENABLED(CONFIG_ZMK_BLE)
    int prof = zmk_ble_active_profile_index();
    if (prof < 0 || prof >= BUTTERFLY_NUM_LEDS) {
        set_all_off();
        return;
    }

    if (zmk_ble_active_profile_is_connected()) {
        int64_t elapsed = k_uptime_get() - state_change_time;
        bool is_dimmed = (CONFIG_BUTTERFLY_TIMEOUT_MS > 0 && elapsed >= CONFIG_BUTTERFLY_TIMEOUT_MS);
        uint8_t brt = is_dimmed ? (uint8_t)CONFIG_BUTTERFLY_DIM_BRIGHTNESS : (uint8_t)CONFIG_BUTTERFLY_BRIGHTNESS;

        if (brt > 0) {
            uint8_t green_comp = (uint8_t)(((uint16_t)brt * 40) / 100);
            pixels[prof] = make_rgb(0, green_comp, brt);
        }
        update_leds(pixels);

        if (!is_dimmed && CONFIG_BUTTERFLY_TIMEOUT_MS > 0) {
            int64_t remaining = CONFIG_BUTTERFLY_TIMEOUT_MS - elapsed;
            if (remaining > 0) {
                k_work_reschedule(&butterfly_work, K_MSEC(remaining + 10));
            }
        }
    } else {
        blink_state = !blink_state;
        if (blink_state) {
            uint8_t brt = (uint8_t)CONFIG_BUTTERFLY_BRIGHTNESS;
            uint8_t green_comp = (uint8_t)(((uint16_t)brt * 70) / 100);
            pixels[prof] = make_rgb(0, green_comp, brt);
        } else {
            pixels[prof] = make_rgb(0, 0, 0);
        }
        update_leds(pixels);

        k_work_reschedule(&butterfly_work, K_MSEC(CONFIG_BUTTERFLY_BLINK_MS));
    }
    return;
#endif

    set_all_off();
}

void butterfly_status_refresh(void) {
    if (!is_battery_gauge) {
        state_change_time = k_uptime_get();
        blink_state = false;
    }
    k_work_reschedule(&butterfly_work, K_NO_WAIT);
}

void butterfly_show_battery(void) {
    uint8_t soc = zmk_battery_state_of_charge();
    if (soc <= 15) {
#if IS_ENABLED(CONFIG_KEYBOARDIO_PREONIC_SOUND)
        preonic_sound_play_low_battery_warning();
#endif
    }
    boot_anim_done = true;
    is_battery_gauge = true;
    k_work_reschedule(&butterfly_work, K_NO_WAIT);
}

void butterfly_set_macro_mode(enum butterfly_macro_mode mode) {
    current_macro_mode = mode;
    if (mode == BUTTERFLY_MACRO_REC_1 || mode == BUTTERFLY_MACRO_REC_2 || mode == BUTTERFLY_MACRO_REC_3) {
        macro_anim_start_time = k_uptime_get();
    } else if (mode == BUTTERFLY_MACRO_PLAY_1 || mode == BUTTERFLY_MACRO_PLAY_2 || mode == BUTTERFLY_MACRO_PLAY_3) {
        macro_play_end_time = k_uptime_get() + 150;
    } else {
        state_change_time = k_uptime_get();
    }
    k_work_reschedule(&butterfly_work, K_NO_WAIT);
}

void butterfly_show_password_length(uint8_t length) {
    uint8_t wings = 1;
    if (length >= 24) {
        wings = 4;
    } else if (length >= 20) {
        wings = 3;
    } else if (length >= 16) {
        wings = 2;
    } else {
        wings = 1;
    }
    pw_gauge_wings = wings;
    pw_gauge_end_time = k_uptime_get() + 2000;
    boot_anim_done = true;
    k_work_reschedule(&butterfly_work, K_NO_WAIT);
}

void butterfly_show_password_success(void) {
    pw_success_anim = true;
    pw_success_end_time = k_uptime_get() + 200;
    boot_anim_done = true;
    k_work_reschedule(&butterfly_work, K_NO_WAIT);
}

static int butterfly_event_listener(const zmk_event_t *eh) {
    struct zmk_activity_state_changed *act_ev = as_zmk_activity_state_changed(eh);
    if (act_ev != NULL) {
        current_activity = act_ev->state;
        if (current_activity == ZMK_ACTIVITY_SLEEP) {
            is_battery_gauge = false;
            k_work_cancel_delayable(&butterfly_work);
            set_all_off();
            return 0;
        }
    }

    struct zmk_battery_state_changed *batt_ev = as_zmk_battery_state_changed(eh);
    if (batt_ev != NULL) {
        uint8_t soc = batt_ev->state_of_charge;
        if (soc <= 15) {
            if (!low_battery_warned) {
                low_battery_warned = true;
#if IS_ENABLED(CONFIG_KEYBOARDIO_PREONIC_SOUND)
                preonic_sound_play_low_battery_warning();
#endif
            }
        } else if (soc >= 20) {
            low_battery_warned = false;
        }
        return 0;
    }

    const struct zmk_position_state_changed *pos_ev = as_zmk_position_state_changed(eh);
    if (pos_ev != NULL) {
        boot_anim_done = true;

        if (pos_ev->state) {
            // Key press
            if (zmk_keymap_layer_active(FN_LAYER_INDEX) || zmk_keymap_layer_active(TRI_LAYER_INDEX)) {
                if (pos_ev->position == B_KEY_POSITION) {
                    butterfly_show_battery();
                    return 0;
                } else if (pos_ev->position == P_KEY_POSITION) {
                    preonic_type_battery_status();
                    return 0;
                }
            }
        } else {
            // Key release: if battery gauge is currently showing, turn off immediately on B release or layer exit
            if (is_battery_gauge) {
                if (pos_ev->position == B_KEY_POSITION ||
                    (!zmk_keymap_layer_active(FN_LAYER_INDEX) && !zmk_keymap_layer_active(TRI_LAYER_INDEX))) {
                    is_battery_gauge = false;
                    state_change_time = k_uptime_get();
                    k_work_reschedule(&butterfly_work, K_NO_WAIT);
                    return 0;
                }
            }
            return 0;
        }
    }

    #if IS_ENABLED(CONFIG_ZMK_USB)
    const struct zmk_usb_conn_state_changed *usb_ev = as_zmk_usb_conn_state_changed(eh);
    if (usb_ev != NULL) {
        LOG_INF("USB connection state changed to: %d", usb_ev->conn_state);
        if (usb_ev->conn_state == ZMK_USB_CONN_NONE) {
            // USB cable disconnected: cancel boot work and auto-switch to BLE mode
            k_work_cancel_delayable(&boot_endpoint_work);
            if (zmk_endpoint_get_preferred_transport() != ZMK_TRANSPORT_BLE) {
                LOG_INF("USB disconnected: auto-switching preferred transport to BLE");
                zmk_endpoint_set_preferred_transport(ZMK_TRANSPORT_BLE);
            }
        } else if (usb_ev->conn_state == ZMK_USB_CONN_HID) {
            // USB cable plugged into PC host with HID ready: cancel boot work and switch to USB
            k_work_cancel_delayable(&boot_endpoint_work);
            if (zmk_endpoint_get_preferred_transport() != ZMK_TRANSPORT_USB) {
                LOG_INF("USB HID host connected: auto-switching preferred transport to USB");
                zmk_endpoint_set_preferred_transport(ZMK_TRANSPORT_USB);
            }
        } else if (usb_ev->conn_state == ZMK_USB_CONN_POWERED) {
            // Connected to wall charger / power bank: keep BLE mode active!
            LOG_INF("USB connected to power-only source (charger): maintaining BLE transport");
        }
        butterfly_status_refresh();
        return 0;
    }
#endif

    butterfly_status_refresh();
    return 0;
}

ZMK_LISTENER(butterfly_status, butterfly_event_listener);
#if IS_ENABLED(CONFIG_ZMK_BLE)
ZMK_SUBSCRIPTION(butterfly_status, zmk_ble_active_profile_changed);
#endif
#if IS_ENABLED(CONFIG_ZMK_USB) || IS_ENABLED(CONFIG_ZMK_BLE)
ZMK_SUBSCRIPTION(butterfly_status, zmk_endpoint_changed);
#endif
#if IS_ENABLED(CONFIG_ZMK_USB)
ZMK_SUBSCRIPTION(butterfly_status, zmk_usb_conn_state_changed);
#endif
ZMK_SUBSCRIPTION(butterfly_status, zmk_position_state_changed);
ZMK_SUBSCRIPTION(butterfly_status, zmk_activity_state_changed);
ZMK_SUBSCRIPTION(butterfly_status, zmk_battery_state_changed);

static void boot_endpoint_work_handler(struct k_work *work) {
    ARG_UNUSED(work);
#if IS_ENABLED(CONFIG_ZMK_USB)
    enum zmk_usb_conn_state conn = zmk_usb_get_conn_state();
    LOG_INF("Boot endpoint check: USB conn state = %d, preferred transport = %d",
            conn, zmk_endpoint_get_preferred_transport());

    if (conn == ZMK_USB_CONN_NONE || conn == ZMK_USB_CONN_POWERED) {
        // Running on battery or charger: switch to BLE mode
        if (zmk_endpoint_get_preferred_transport() != ZMK_TRANSPORT_BLE) {
            LOG_INF("Boot on battery/charger: selecting BLE transport");
            zmk_endpoint_set_preferred_transport(ZMK_TRANSPORT_BLE);
        }
    } else if (conn == ZMK_USB_CONN_HID) {
        // Booted with USB cable connected to PC host
        if (zmk_endpoint_get_preferred_transport() != ZMK_TRANSPORT_USB) {
            LOG_INF("Booted with USB HID connected: selecting USB transport");
            zmk_endpoint_set_preferred_transport(ZMK_TRANSPORT_USB);
        }
    }
#endif
    butterfly_status_refresh();
}

static int butterfly_init(void) {
    k_work_init_delayable(&butterfly_work, butterfly_work_handler);
    k_work_init_delayable(&boot_endpoint_work, boot_endpoint_work_handler);

    bool wake_from_off = false;
#if defined(NRF_POWER) || defined(NRFX_RESET_REASON_H)
    uint32_t reason = nrfx_reset_reason_get();
    if (reason & (NRFX_RESET_REASON_OFF_MASK
#if NRFX_RESET_REASON_HAS_LPCOMP
                | NRFX_RESET_REASON_LPCOMP_MASK
#endif
#if NRFX_RESET_REASON_HAS_NFC
                | NRFX_RESET_REASON_NFC_MASK
#endif
       )) {
        wake_from_off = true;
    }
    // Clear OFF reset reason now that all init routines have completed
    nrfx_reset_reason_clear(NRFX_RESET_REASON_OFF_MASK);
#endif

    // Safely defer initial endpoint check after kernel and settings initialization
    k_work_reschedule(&boot_endpoint_work, K_MSEC(400));

#if CONFIG_BUTTERFLY_BOOT_ANIM_MS > 0
    if (wake_from_off) {
        boot_anim_done = true;
    } else {
        boot_anim_done = false;
        boot_start_time = k_uptime_get();
    }
#else
    boot_anim_done = true;
#endif

    uint8_t initial_soc = zmk_battery_state_of_charge();
    if (initial_soc <= 15 && initial_soc > 0) {
        low_battery_warned = true;
    }

    butterfly_status_refresh();
    return 0;
}

SYS_INIT(butterfly_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
