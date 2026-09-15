/*
 * Copyright (c) 2026 Keyboardio Preonic Custom Firmware
 * SPDX-License-Identifier: MIT
 */

#include <zephyr/kernel.h>
#include <zephyr/init.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/sys/ring_buffer.h>
#include <zephyr/sys/util.h>
#include <zephyr/logging/log.h>
#include <zephyr/settings/settings.h>
#include <string.h>
#include <errno.h>

#include <zmk/keymap.h>
#include <zmk/behavior.h>
#include <zmk/battery.h>
#include <zmk/ble.h>
#include <zmk/endpoints.h>
#include <zmk/usb.h>
#include <zmk/usb_hid.h>
#include <zmk/event_manager.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/events/activity_state_changed.h>
#include <zmk/events/layer_state_changed.h>

#include "preonic_studio.h"
#include "preonic_sound.h"
#include "butterfly_status.h"
#include "dynamic_macro.h"
#include "password_generator.h"

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#define RX_RING_BUF_SIZE 256
#define AUTO_LOCK_TIMEOUT_SEC 300
#define UNLOCK_KEY_POSITION 40
#define FN_LAYER_INDEX 3
#define TRI_LAYER_INDEX 4

#define NUM_LAYERS PREONIC_STUDIO_NUM_LAYERS
#define NUM_ROWS 5
#define NUM_COLS 12
#define FW_VERSION_MAJOR 2
#define FW_VERSION_MINOR 0
#define FW_VERSION_PATCH 0
#define DEVICE_NAME "Preonic"

#if DT_HAS_CHOSEN(zmk_studio_rpc_uart)
#define STUDIO_UART_DEV DT_CHOSEN(zmk_studio_rpc_uart)
#elif DT_NODE_EXISTS(DT_NODELABEL(cdc_acm_uart0))
#define STUDIO_UART_DEV DT_NODELABEL(cdc_acm_uart0)
#elif DT_HAS_COMPAT_STATUS_OKAY(zephyr_cdc_acm_uart)
#define STUDIO_UART_DEV DT_COMPAT_GET_ANY_STATUS_OKAY(zephyr_cdc_acm_uart)
#else
#define STUDIO_UART_DEV DT_INVALID_NODE
#endif

#if DT_NODE_EXISTS(STUDIO_UART_DEV)
static const struct device *const uart_dev = DEVICE_DT_GET(STUDIO_UART_DEV);
#else
static const struct device *const uart_dev = NULL;
#endif

/* Dynamic macro raw step structure */
struct __packed dyn_macro_step {
    uint32_t keycode;
    uint8_t pressed;
};

/* Rotary knob layer configuration */
struct studio_knob_config {
    uint8_t cw_beh;
    uint32_t cw_param;
    uint8_t ccw_beh;
    uint32_t ccw_param;
    uint8_t pulses_per_detent;
};

/* Mouse acceleration parameters */
struct studio_mouse_config {
    uint16_t mmv_time_ms;
    uint8_t mmv_exp;
    uint16_t msc_time_ms;
    uint8_t msc_exp;
    uint8_t msc_step;
};

/* Piezo audio configuration */
struct studio_audio_config {
    uint16_t click_freq_hz;
    uint8_t click_dur_ms;
};

static struct studio_knob_config knob_configs[NUM_LAYERS] = {
    [0 ... NUM_LAYERS - 1] = {
        .cw_beh = 0x01,
        .cw_param = 0x80 | 0xE9,
        .ccw_beh = 0x01,
        .ccw_param = 0x80 | 0xEA,
        .pulses_per_detent = 2
    }
};

static struct studio_mouse_config mouse_cfg = {
    .mmv_time_ms = 500,
    .mmv_exp = 1,
    .msc_time_ms = 300,
    .msc_exp = 1,
    .msc_step = 10,
};

static struct studio_audio_config audio_cfg = {
    .click_freq_hz = 3000,
    .click_dur_ms = 5,
};

static bool studio_locked = true;
static bool was_dtr_active = false;
static preonic_studio_tx_fn test_tx_hook = NULL;

static uint8_t rx_buffer[RX_RING_BUF_SIZE];
static struct ring_buf rx_ringbuf;
static struct k_mutex tx_mutex;
static struct k_work process_work;
static struct k_work_delayable auto_lock_work;

enum rx_parser_state {
    STATE_WAIT_SOF,
    STATE_CMD,
    STATE_SEQ,
    STATE_LEN,
    STATE_DATA,
    STATE_CHKSUM,
    STATE_EOF,
};

static enum rx_parser_state current_state = STATE_WAIT_SOF;
static uint8_t current_cmd = 0;
static uint8_t current_seq = 0;
static uint8_t current_len = 0;
static uint8_t data_idx = 0;
static uint8_t payload_buf[PREONIC_STUDIO_MAX_PAYLOAD];
static uint8_t expected_chksum = 0;

void preonic_studio_set_tx_hook(preonic_studio_tx_fn hook) {
    test_tx_hook = hook;
}

static void send_packet(uint8_t cmd, uint8_t seq, const uint8_t *data, uint8_t len) {
    if (len > PREONIC_STUDIO_MAX_PAYLOAD) {
        len = PREONIC_STUDIO_MAX_PAYLOAD;
    }

    if (test_tx_hook) {
        test_tx_hook(cmd, seq, data, len);
        return;
    }

    if (!uart_dev || !device_is_ready(uart_dev)) {
        return;
    }

    uint8_t chk = cmd + seq + len;
    for (uint8_t i = 0; i < len; i++) {
        chk += data[i];
    }

    k_mutex_lock(&tx_mutex, K_FOREVER);
    uart_poll_out(uart_dev, PREONIC_STUDIO_SOF);
    uart_poll_out(uart_dev, cmd);
    uart_poll_out(uart_dev, seq);
    uart_poll_out(uart_dev, len);
    for (uint8_t i = 0; i < len; i++) {
        uart_poll_out(uart_dev, data[i]);
    }
    uart_poll_out(uart_dev, chk);
    uart_poll_out(uart_dev, PREONIC_STUDIO_EOF);
    k_mutex_unlock(&tx_mutex);
}

static bool check_locked_rejection(uint8_t cmd, uint8_t seq) {
    if (studio_locked) {
        uint8_t err = STATUS_ERR_LOCKED;
        send_packet(cmd, seq, &err, 1);
        return true;
    }
    return false;
}

static char hid_to_ascii(uint32_t keycode, bool shifted) {
    if (keycode >= 0x04 && keycode <= 0x1D) {
        return shifted ? ('A' + (keycode - 0x04)) : ('a' + (keycode - 0x04));
    }
    if (keycode >= 0x1E && keycode <= 0x26) {
        static const char shifted_nums[] = "!@#$%^&*(";
        return shifted ? shifted_nums[keycode - 0x1E] : ('1' + (keycode - 0x1E));
    }
    if (keycode == 0x27) return shifted ? ')' : '0';
    if (keycode == 0x28) return '\n';
    if (keycode == 0x2B) return '\t';
    if (keycode == 0x2C) return ' ';
    if (keycode == 0x2D) return shifted ? '_' : '-';
    if (keycode == 0x2E) return shifted ? '+' : '=';
    if (keycode == 0x2F) return shifted ? '{' : '[';
    if (keycode == 0x30) return shifted ? '}' : ']';
    if (keycode == 0x31) return shifted ? '|' : '\\';
    if (keycode == 0x33) return shifted ? ':' : ';';
    if (keycode == 0x34) return shifted ? '"' : '\'';
    if (keycode == 0x35) return shifted ? '~' : '`';
    if (keycode == 0x36) return shifted ? '<' : ',';
    if (keycode == 0x37) return shifted ? '>' : '.';
    if (keycode == 0x38) return shifted ? '?' : '/';
    return '?';
}

static uint8_t macro_steps_to_ascii(const struct dyn_macro_step *steps, uint16_t step_count, char *out_text, uint8_t max_len) {
    uint8_t text_len = 0;
    bool shift_active = false;
    for (uint16_t i = 0; i < step_count && text_len < max_len; i++) {
        if (steps[i].keycode == 0xE1 /* HID_KEY_LEFTSHIFT */) {
            shift_active = (steps[i].pressed != 0);
            continue;
        }
        if (steps[i].pressed) {
            out_text[text_len++] = hid_to_ascii(steps[i].keycode, shift_active);
        }
    }
    return text_len;
}

static uint8_t behavior_dev_to_type(const char *dev_name) {
    if (!dev_name) {
        return PREONIC_BEH_NONE;
    }
    if (strstr(dev_name, "caps_word") != NULL) {
        return PREONIC_BEH_CAPS_WORD;
    }
    if (strstr(dev_name, "tog") != NULL || strstr(dev_name, "toggle_layer") != NULL) {
        return PREONIC_BEH_TOG;
    }
    if (strstr(dev_name, "mkp") != NULL || strstr(dev_name, "mouse_key") != NULL) {
        return PREONIC_BEH_MKP;
    }
    if (strstr(dev_name, "mod_tap") != NULL || strcmp(dev_name, "mt") == 0) {
        return PREONIC_BEH_MT;
    }
    if (strstr(dev_name, "layer_tap") != NULL || strcmp(dev_name, "lt") == 0) {
        return PREONIC_BEH_LT;
    }
    if (strstr(dev_name, "sticky_key") != NULL || strcmp(dev_name, "sk") == 0) {
        return PREONIC_BEH_SK;
    }
    if (strstr(dev_name, "sticky_layer") != NULL || strcmp(dev_name, "sl") == 0) {
        return PREONIC_BEH_SL;
    }
    if (strstr(dev_name, "kp") != NULL || strstr(dev_name, "key_press") != NULL) {
        return PREONIC_BEH_KP;
    }
    if (strstr(dev_name, "mo") != NULL || strstr(dev_name, "momentary") != NULL) {
        return PREONIC_BEH_MO;
    }
    if (strstr(dev_name, "to") != NULL || strstr(dev_name, "to_layer") != NULL) {
        return PREONIC_BEH_TO;
    }
    if (strstr(dev_name, "trans") != NULL) {
        return PREONIC_BEH_TRANS;
    }
    if (strstr(dev_name, "none") != NULL) {
        return PREONIC_BEH_NONE;
    }
    if (strstr(dev_name, "bt") != NULL || strstr(dev_name, "bluetooth") != NULL) {
        return PREONIC_BEH_BT;
    }
    if (strstr(dev_name, "out") != NULL || strstr(dev_name, "outputs") != NULL) {
        return PREONIC_BEH_OUT;
    }
    if (strstr(dev_name, "studio_unlock") != NULL) {
        return PREONIC_BEH_STUDIO_UNLOCK;
    }
    if (strstr(dev_name, "reset") != NULL || strstr(dev_name, "bootload") != NULL) {
        return PREONIC_BEH_SYS_RESET;
    }
    return PREONIC_BEH_KP;
}

static const char *behavior_type_to_dev(uint8_t beh_type) {
    switch (beh_type) {
    case PREONIC_BEH_KP:
#if DT_NODE_EXISTS(DT_NODELABEL(kp))
        return DEVICE_DT_NAME(DT_NODELABEL(kp));
#else
        return "key_press";
#endif
    case PREONIC_BEH_MO:
#if DT_NODE_EXISTS(DT_NODELABEL(mo))
        return DEVICE_DT_NAME(DT_NODELABEL(mo));
#else
        return "momentary_layer";
#endif
    case PREONIC_BEH_TO:
#if DT_NODE_EXISTS(DT_NODELABEL(to))
        return DEVICE_DT_NAME(DT_NODELABEL(to));
#else
        return "to_layer";
#endif
    case PREONIC_BEH_TRANS:
#if DT_NODE_EXISTS(DT_NODELABEL(trans))
        return DEVICE_DT_NAME(DT_NODELABEL(trans));
#else
        return "transparent";
#endif
    case PREONIC_BEH_NONE:
#if DT_NODE_EXISTS(DT_NODELABEL(none))
        return DEVICE_DT_NAME(DT_NODELABEL(none));
#else
        return "none";
#endif
    case PREONIC_BEH_BT:
#if DT_NODE_EXISTS(DT_NODELABEL(bt))
        return DEVICE_DT_NAME(DT_NODELABEL(bt));
#else
        return "bluetooth";
#endif
    case PREONIC_BEH_OUT:
#if DT_NODE_EXISTS(DT_NODELABEL(out))
        return DEVICE_DT_NAME(DT_NODELABEL(out));
#else
        return "outputs";
#endif
    case PREONIC_BEH_SYS_RESET:
#if DT_NODE_EXISTS(DT_NODELABEL(sys_reset))
        return DEVICE_DT_NAME(DT_NODELABEL(sys_reset));
#else
        return "sysreset";
#endif
    case PREONIC_BEH_TOG:
#if DT_NODE_EXISTS(DT_NODELABEL(tog))
        return DEVICE_DT_NAME(DT_NODELABEL(tog));
#else
        return "toggle_layer";
#endif
    case PREONIC_BEH_CAPS_WORD:
#if DT_NODE_EXISTS(DT_NODELABEL(caps_word))
        return DEVICE_DT_NAME(DT_NODELABEL(caps_word));
#else
        return "caps_word";
#endif
    case PREONIC_BEH_MT:
#if DT_NODE_EXISTS(DT_NODELABEL(mt))
        return DEVICE_DT_NAME(DT_NODELABEL(mt));
#else
        return "mod_tap";
#endif
    case PREONIC_BEH_LT:
#if DT_NODE_EXISTS(DT_NODELABEL(lt))
        return DEVICE_DT_NAME(DT_NODELABEL(lt));
#else
        return "layer_tap";
#endif
    case PREONIC_BEH_MKP:
#if DT_NODE_EXISTS(DT_NODELABEL(mkp))
        return DEVICE_DT_NAME(DT_NODELABEL(mkp));
#else
        return "mouse_key_press";
#endif
    case PREONIC_BEH_SK:
#if DT_NODE_EXISTS(DT_NODELABEL(sk))
        return DEVICE_DT_NAME(DT_NODELABEL(sk));
#else
        return "sticky_key";
#endif
    case PREONIC_BEH_SL:
#if DT_NODE_EXISTS(DT_NODELABEL(sl))
        return DEVICE_DT_NAME(DT_NODELABEL(sl));
#else
        return "sticky_layer";
#endif
    default:
        return NULL;
    }
}

#if IS_ENABLED(CONFIG_SETTINGS)
static void save_knob_config(uint8_t layer) {
    if (layer >= NUM_LAYERS) return;
    char path[20];
    snprintk(path, sizeof(path), "studio/knob/%u", layer);
    settings_save_one(path, &knob_configs[layer], sizeof(knob_configs[layer]));
}

static void save_mouse_config(void) {
    settings_save_one("studio/mouse", &mouse_cfg, sizeof(mouse_cfg));
}

static void save_audio_config(void) {
    settings_save_one("studio/audio", &audio_cfg, sizeof(audio_cfg));
}
#else
static inline void save_knob_config(uint8_t layer) { ARG_UNUSED(layer); }
static inline void save_mouse_config(void) {}
static inline void save_audio_config(void) {}
#endif

static void check_dtr_status(void) {
    if (!uart_dev || !device_is_ready(uart_dev)) {
        return;
    }
    uint32_t dtr = 0;
    int ret = uart_line_ctrl_get(uart_dev, UART_LINE_CTRL_DTR, &dtr);
    if (ret == 0) {
        if (dtr) {
            was_dtr_active = true;
        } else if (was_dtr_active) {
            was_dtr_active = false;
            if (!studio_locked) {
                LOG_INF("CDC ACM DTR dropped -> host disconnected, locking");
                preonic_studio_lock();
#if IS_ENABLED(CONFIG_KEYBOARDIO_PREONIC_SOUND)
                preonic_sound_play_studio_lock();
#endif
                uint8_t reason = 0x02; // disconnect
                send_packet(EVT_LOCKED, 0, &reason, 1);
            }
        }
    }
}

static void preonic_studio_dispatch_command(uint8_t cmd, uint8_t seq, const uint8_t *data, uint8_t len) {
    // Any valid host command resets the 300s inactivity auto-lock timer
    if (!studio_locked) {
        k_work_reschedule(&auto_lock_work, K_SECONDS(AUTO_LOCK_TIMEOUT_SEC));
    }

    switch (cmd) {
    case CMD_PING: {
        uint8_t status = STATUS_OK;
        send_packet(CMD_PING, seq, &status, 1);
        break;
    }

    case CMD_HANDSHAKE: {
        uint8_t resp[23];
        resp[0] = FW_VERSION_MAJOR;
        resp[1] = FW_VERSION_MINOR;
        resp[2] = FW_VERSION_PATCH;
        resp[3] = studio_locked ? 1 : 0;
        resp[4] = NUM_LAYERS;
        resp[5] = NUM_ROWS;
        resp[6] = NUM_COLS;
        memset(&resp[7], 0, 16);
        strncpy((char *)&resp[7], DEVICE_NAME, 16);
        send_packet(CMD_HANDSHAKE, seq, resp, 23);
        break;
    }

    case CMD_GET_LOCK_STATUS: {
        uint8_t resp[3];
        resp[0] = studio_locked ? 1 : 0;
        uint16_t rem = 0;
        if (!studio_locked) {
            k_ticks_t t = k_work_delayable_remaining_get(&auto_lock_work);
            rem = (uint16_t)(k_ticks_to_ms_near32(t) / 1000);
        }
        resp[1] = rem & 0xFF;
        resp[2] = (rem >> 8) & 0xFF;
        send_packet(CMD_GET_LOCK_STATUS, seq, resp, 3);
        break;
    }

    case CMD_LOCK: {
        preonic_studio_lock();
#if IS_ENABLED(CONFIG_KEYBOARDIO_PREONIC_SOUND)
        preonic_sound_play_studio_lock();
#endif
        uint8_t status = STATUS_OK;
        send_packet(CMD_LOCK, seq, &status, 1);
        break;
    }

    case CMD_GET_STATUS: {
        uint8_t resp[7];
        uint8_t soc = zmk_battery_state_of_charge();
        if (soc > 100) soc = 100;
        uint16_t mv = 3300 + (uint16_t)soc * 9;
        resp[0] = mv & 0xFF;
        resp[1] = (mv >> 8) & 0xFF;
        resp[2] = soc;
#if IS_ENABLED(CONFIG_ZMK_BLE)
        int prof = zmk_ble_active_profile_index();
        resp[3] = (prof >= 0) ? (uint8_t)prof : 0;
#else
        resp[3] = 0;
#endif
        bool is_usb = false;
#if IS_ENABLED(CONFIG_ZMK_USB)
        struct zmk_endpoint_instance ep = zmk_endpoint_get_selected();
        if (zmk_endpoint_get_preferred_transport() != ZMK_TRANSPORT_BLE &&
            (ep.transport == ZMK_TRANSPORT_USB || zmk_usb_is_hid_ready())) {
            is_usb = true;
        }
#endif
        resp[4] = is_usb ? 1 : 0;
        resp[5] = preonic_sound_is_master_enabled() ? 1 : 0;
        resp[6] = preonic_sound_is_clicky_enabled() ? 1 : 0;
        send_packet(CMD_GET_STATUS, seq, resp, 7);
        break;
    }

    case CMD_GET_KEY: {
        if (len < 2) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_GET_KEY, seq, &err, 1);
            break;
        }
        uint8_t layer = data[0];
        uint8_t key_idx = data[1];
        if (layer >= NUM_LAYERS) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_GET_KEY, seq, &err, 1);
            break;
        }
        const struct zmk_behavior_binding *b = zmk_keymap_get_layer_binding_at_idx(layer, key_idx);
        uint8_t resp[11] = {0};
        resp[0] = layer;
        resp[1] = key_idx;
        uint8_t beh_type = 0x05; // none
        uint32_t p1 = 0, p2 = 0;
        if (b) {
            p1 = b->param1;
            p2 = b->param2;
            beh_type = behavior_dev_to_type(b->behavior_dev);
        }
        resp[2] = beh_type;
        resp[3] = p1 & 0xFF;
        resp[4] = (p1 >> 8) & 0xFF;
        resp[5] = (p1 >> 16) & 0xFF;
        resp[6] = (p1 >> 24) & 0xFF;
        resp[7] = p2 & 0xFF;
        resp[8] = (p2 >> 8) & 0xFF;
        resp[9] = (p2 >> 16) & 0xFF;
        resp[10] = (p2 >> 24) & 0xFF;
        send_packet(CMD_GET_KEY, seq, resp, 11);
        break;
    }

    case CMD_SET_KEY: {
        if (check_locked_rejection(cmd, seq)) break;
        if (len < 11) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_SET_KEY, seq, &err, 1);
            break;
        }
        uint8_t layer = data[0];
        uint8_t key_idx = data[1];
        uint8_t beh_type = data[2];
        uint32_t p1 = data[3] | ((uint32_t)data[4] << 8) | ((uint32_t)data[5] << 16) | ((uint32_t)data[6] << 24);
        uint32_t p2 = data[7] | ((uint32_t)data[8] << 8) | ((uint32_t)data[9] << 16) | ((uint32_t)data[10] << 24);

        if (layer >= NUM_LAYERS) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_SET_KEY, seq, &err, 1);
            break;
        }

#if IS_ENABLED(CONFIG_ZMK_KEYMAP_SETTINGS_STORAGE)
        const char *dev_name = behavior_type_to_dev(beh_type);
        if (!dev_name) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_SET_KEY, seq, &err, 1);
            break;
        }
        struct zmk_behavior_binding binding = {
            .behavior_dev = dev_name,
            .param1 = p1,
            .param2 = p2,
        };
        int ret = zmk_keymap_set_layer_binding_at_idx(layer, key_idx, binding);
        uint8_t status = (ret == 0) ? STATUS_OK : STATUS_ERR_INVALID;
        send_packet(CMD_SET_KEY, seq, &status, 1);
#else
        uint8_t status = STATUS_ERR_INVALID;
        send_packet(CMD_SET_KEY, seq, &status, 1);
#endif
        break;
    }

    case CMD_SAVE_KEYMAP: {
        if (check_locked_rejection(cmd, seq)) break;
#if IS_ENABLED(CONFIG_ZMK_KEYMAP_SETTINGS_STORAGE)
        int ret = zmk_keymap_save_changes();
        uint8_t status = (ret == 0) ? STATUS_OK : STATUS_ERR_INVALID;
        send_packet(CMD_SAVE_KEYMAP, seq, &status, 1);
#else
        uint8_t status = STATUS_ERR_INVALID;
        send_packet(CMD_SAVE_KEYMAP, seq, &status, 1);
#endif
        break;
    }

    case CMD_DISCARD_KEYMAP: {
        if (check_locked_rejection(cmd, seq)) break;
#if IS_ENABLED(CONFIG_ZMK_KEYMAP_SETTINGS_STORAGE)
        int ret = zmk_keymap_discard_changes();
        uint8_t status = (ret == 0) ? STATUS_OK : STATUS_ERR_INVALID;
        send_packet(CMD_DISCARD_KEYMAP, seq, &status, 1);
#else
        uint8_t status = STATUS_ERR_INVALID;
        send_packet(CMD_DISCARD_KEYMAP, seq, &status, 1);
#endif
        break;
    }

    case CMD_GET_KNOB: {
        if (len < 1) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_GET_KNOB, seq, &err, 1);
            break;
        }
        uint8_t layer = data[0];
        if (layer >= NUM_LAYERS) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_GET_KNOB, seq, &err, 1);
            break;
        }
        uint8_t resp[12];
        resp[0] = layer;
        resp[1] = knob_configs[layer].cw_beh;
        resp[2] = knob_configs[layer].cw_param & 0xFF;
        resp[3] = (knob_configs[layer].cw_param >> 8) & 0xFF;
        resp[4] = (knob_configs[layer].cw_param >> 16) & 0xFF;
        resp[5] = (knob_configs[layer].cw_param >> 24) & 0xFF;
        resp[6] = knob_configs[layer].ccw_beh;
        resp[7] = knob_configs[layer].ccw_param & 0xFF;
        resp[8] = (knob_configs[layer].ccw_param >> 8) & 0xFF;
        resp[9] = (knob_configs[layer].ccw_param >> 16) & 0xFF;
        resp[10] = (knob_configs[layer].ccw_param >> 24) & 0xFF;
        resp[11] = knob_configs[layer].pulses_per_detent;
        send_packet(CMD_GET_KNOB, seq, resp, 12);
        break;
    }

    case CMD_SET_KNOB: {
        if (check_locked_rejection(cmd, seq)) break;
        if (len < 12) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_SET_KNOB, seq, &err, 1);
            break;
        }
        uint8_t layer = data[0];
        if (layer >= NUM_LAYERS) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_SET_KNOB, seq, &err, 1);
            break;
        }
        knob_configs[layer].cw_beh = data[1];
        knob_configs[layer].cw_param = data[2] | ((uint32_t)data[3] << 8) | ((uint32_t)data[4] << 16) | ((uint32_t)data[5] << 24);
        knob_configs[layer].ccw_beh = data[6];
        knob_configs[layer].ccw_param = data[7] | ((uint32_t)data[8] << 8) | ((uint32_t)data[9] << 16) | ((uint32_t)data[10] << 24);
        knob_configs[layer].pulses_per_detent = data[11];
        save_knob_config(layer);

        uint8_t status = STATUS_OK;
        send_packet(CMD_SET_KNOB, seq, &status, 1);
        break;
    }

    case CMD_GET_MACRO: {
        if (check_locked_rejection(cmd, seq)) break;
        if (len < 1) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_GET_MACRO, seq, &err, 1);
            break;
        }
        uint8_t slot_num = data[0];
        if (slot_num < 1 || slot_num > 3) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_GET_MACRO, seq, &err, 1);
            break;
        }

        struct dyn_macro_step steps[32];
        uint16_t copied = dynamic_macro_get_slot_steps(slot_num, steps, sizeof(steps));
        uint16_t step_count = copied / sizeof(struct dyn_macro_step);

        char text[32];
        uint8_t text_len = macro_steps_to_ascii(steps, step_count, text, sizeof(text));

        uint8_t resp[4 + 32];
        resp[0] = slot_num;
        resp[1] = step_count & 0xFF;
        resp[2] = (step_count >> 8) & 0xFF;
        resp[3] = text_len;
        if (text_len > 0) {
            memcpy(&resp[4], text, text_len);
        }
        send_packet(CMD_GET_MACRO, seq, resp, 4 + text_len);
        break;
    }

    case CMD_SET_MACRO: {
        if (check_locked_rejection(cmd, seq)) break;
        if (len < 2) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_SET_MACRO, seq, &err, 1);
            break;
        }
        uint8_t slot_num = data[0];
        uint8_t text_len = data[1];
        if (slot_num < 1 || slot_num > 3 || text_len > len - 2) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_SET_MACRO, seq, &err, 1);
            break;
        }

        int ret = dynamic_macro_set_slot_text(slot_num, (const char *)&data[2], text_len);
        uint8_t status = (ret == 0) ? STATUS_OK : STATUS_ERR_INVALID;
        send_packet(CMD_SET_MACRO, seq, &status, 1);
        break;
    }

    case CMD_PLAY_MACRO: {
        if (check_locked_rejection(cmd, seq)) break;
        if (len < 1) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_PLAY_MACRO, seq, &err, 1);
            break;
        }
        uint8_t slot_num = data[0];
        if (slot_num < 1 || slot_num > 3) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_PLAY_MACRO, seq, &err, 1);
            break;
        }
        dynamic_macro_play(slot_num);
        uint8_t status = STATUS_OK;
        send_packet(CMD_PLAY_MACRO, seq, &status, 1);
        break;
    }

    case CMD_GET_PW_CONFIG: {
        uint8_t def_len = 16;
        uint8_t interval = 12;
        uint8_t specials_len = 0;
        char specials[32] = {0};
        password_generator_get_config(&def_len, &interval, specials, &specials_len);

        uint8_t resp[35];
        resp[0] = def_len;
        resp[1] = interval;
        resp[2] = specials_len;
        memcpy(&resp[3], specials, 32);
        send_packet(CMD_GET_PW_CONFIG, seq, resp, 35);
        break;
    }

    case CMD_SET_PW_CONFIG: {
        if (check_locked_rejection(cmd, seq)) break;
        if (len < 3) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_SET_PW_CONFIG, seq, &err, 1);
            break;
        }
        uint8_t def_len = data[0];
        uint8_t interval = data[1];
        uint8_t specials_len = data[2];
        if (specials_len > 32 || specials_len > len - 3) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_SET_PW_CONFIG, seq, &err, 1);
            break;
        }

        int ret = password_generator_set_config(def_len, interval, (const char *)&data[3], specials_len);
        uint8_t status = (ret == 0) ? STATUS_OK : STATUS_ERR_INVALID;
        send_packet(CMD_SET_PW_CONFIG, seq, &status, 1);
        break;
    }

    case CMD_GET_MOUSE_CFG: {
        uint8_t resp[7];
        resp[0] = mouse_cfg.mmv_time_ms & 0xFF;
        resp[1] = (mouse_cfg.mmv_time_ms >> 8) & 0xFF;
        resp[2] = mouse_cfg.mmv_exp;
        resp[3] = mouse_cfg.msc_time_ms & 0xFF;
        resp[4] = (mouse_cfg.msc_time_ms >> 8) & 0xFF;
        resp[5] = mouse_cfg.msc_exp;
        resp[6] = mouse_cfg.msc_step;
        send_packet(CMD_GET_MOUSE_CFG, seq, resp, 7);
        break;
    }

    case CMD_SET_MOUSE_CFG: {
        if (check_locked_rejection(cmd, seq)) break;
        if (len < 7) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_SET_MOUSE_CFG, seq, &err, 1);
            break;
        }
        mouse_cfg.mmv_time_ms = data[0] | ((uint16_t)data[1] << 8);
        mouse_cfg.mmv_exp = data[2];
        mouse_cfg.msc_time_ms = data[3] | ((uint16_t)data[4] << 8);
        mouse_cfg.msc_exp = data[5];
        mouse_cfg.msc_step = data[6];
        save_mouse_config();

        uint8_t status = STATUS_OK;
        send_packet(CMD_SET_MOUSE_CFG, seq, &status, 1);
        break;
    }

    case CMD_GET_AUDIO_CFG: {
        uint8_t resp[5];
        resp[0] = preonic_sound_is_master_enabled() ? 1 : 0;
        resp[1] = preonic_sound_is_clicky_enabled() ? 1 : 0;
        resp[2] = audio_cfg.click_freq_hz & 0xFF;
        resp[3] = (audio_cfg.click_freq_hz >> 8) & 0xFF;
        resp[4] = audio_cfg.click_dur_ms;
        send_packet(CMD_GET_AUDIO_CFG, seq, resp, 5);
        break;
    }

    case CMD_SET_AUDIO_CFG: {
        if (check_locked_rejection(cmd, seq)) break;
        if (len < 5) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_SET_AUDIO_CFG, seq, &err, 1);
            break;
        }
        bool master_req = (data[0] != 0);
        bool clicky_req = (data[1] != 0);
        if (master_req != preonic_sound_is_master_enabled()) {
            preonic_sound_toggle_master();
        }
        if (clicky_req != preonic_sound_is_clicky_enabled()) {
            preonic_sound_toggle_clicky();
        }
        audio_cfg.click_freq_hz = data[2] | ((uint16_t)data[3] << 8);
        audio_cfg.click_dur_ms = data[4];
        save_audio_config();

        uint8_t status = STATUS_OK;
        send_packet(CMD_SET_AUDIO_CFG, seq, &status, 1);
        break;
    }

    case CMD_TEST_PIEZO: {
        if (check_locked_rejection(cmd, seq)) break;
        if (len < 4) {
            uint8_t err = STATUS_ERR_INVALID;
            send_packet(CMD_TEST_PIEZO, seq, &err, 1);
            break;
        }
        uint16_t freq = data[0] | ((uint16_t)data[1] << 8);
        uint16_t dur = data[2] | ((uint16_t)data[3] << 8);
        preonic_sound_play_tone_ms(freq, dur);

        uint8_t status = STATUS_OK;
        send_packet(CMD_TEST_PIEZO, seq, &status, 1);
        break;
    }

    default: {
        uint8_t err = STATUS_ERR_INVALID;
        send_packet(cmd, seq, &err, 1);
        break;
    }
    }
}

void preonic_studio_process_byte(uint8_t byte) {
    switch (current_state) {
    case STATE_WAIT_SOF:
        if (byte == PREONIC_STUDIO_SOF) {
            current_state = STATE_CMD;
        }
        break;

    case STATE_CMD:
        current_cmd = byte;
        current_state = STATE_SEQ;
        break;

    case STATE_SEQ:
        current_seq = byte;
        current_state = STATE_LEN;
        break;

    case STATE_LEN:
        current_len = byte;
        if (current_len > PREONIC_STUDIO_MAX_PAYLOAD) {
            current_state = STATE_WAIT_SOF;
            break;
        }
        data_idx = 0;
        if (current_len == 0) {
            current_state = STATE_CHKSUM;
        } else {
            current_state = STATE_DATA;
        }
        break;

    case STATE_DATA:
        payload_buf[data_idx++] = byte;
        if (data_idx >= current_len) {
            current_state = STATE_CHKSUM;
        }
        break;

    case STATE_CHKSUM:
        expected_chksum = byte;
        current_state = STATE_EOF;
        break;

    case STATE_EOF:
        if (byte == PREONIC_STUDIO_EOF) {
            uint8_t calc_chk = current_cmd + current_seq + current_len;
            for (uint8_t i = 0; i < current_len; i++) {
                calc_chk += payload_buf[i];
            }
            if (calc_chk == expected_chksum) {
                preonic_studio_dispatch_command(current_cmd, current_seq, payload_buf, current_len);
            } else {
                LOG_WRN("Preonic Studio checksum error: calc 0x%02x != recv 0x%02x", calc_chk, expected_chksum);
            }
        }
        current_state = STATE_WAIT_SOF;
        break;

    default:
        current_state = STATE_WAIT_SOF;
        break;
    }
}

void preonic_studio_unlock(void) {
    studio_locked = false;
    k_work_reschedule(&auto_lock_work, K_SECONDS(AUTO_LOCK_TIMEOUT_SEC));
    LOG_INF("Preonic Studio physical presence UNLOCKED");
}

void preonic_studio_lock(void) {
    studio_locked = true;
    k_work_cancel_delayable(&auto_lock_work);
    LOG_INF("Preonic Studio LOCKED");
}

bool preonic_studio_is_locked(void) {
    return studio_locked;
}

static void process_work_handler(struct k_work *work) {
    ARG_UNUSED(work);
    check_dtr_status();
    uint8_t byte;
    while (ring_buf_get(&rx_ringbuf, &byte, 1) == 1) {
        preonic_studio_process_byte(byte);
    }
}

static void auto_lock_work_handler(struct k_work *work) {
    ARG_UNUSED(work);
    if (!studio_locked) {
        LOG_INF("Preonic Studio inactivity timeout (300s) -> locking");
        preonic_studio_lock();
#if IS_ENABLED(CONFIG_KEYBOARDIO_PREONIC_SOUND)
        preonic_sound_play_studio_lock();
#endif
        uint8_t reason = 0x01; // timeout
        send_packet(EVT_LOCKED, 0, &reason, 1);
    }
}

static void uart_cb(const struct device *dev, void *user_data) {
    ARG_UNUSED(user_data);

    while (uart_irq_update(dev) && uart_irq_is_pending(dev)) {
        if (uart_irq_rx_ready(dev)) {
            uint8_t buf[32];
            int len = uart_fifo_read(dev, buf, sizeof(buf));
            if (len > 0) {
                ring_buf_put(&rx_ringbuf, buf, len);
                k_work_submit(&process_work);
            }
        }
        if (uart_irq_tx_ready(dev)) {
            // Poll-out is used for CDC ACM responses
        }
    }
}

static int preonic_studio_event_listener(const zmk_event_t *eh) {
    const struct zmk_position_state_changed *pos_ev = as_zmk_position_state_changed(eh);
    if (pos_ev != NULL) {
        if (was_dtr_active) {
            uint8_t key_evt[2];
            key_evt[0] = (uint8_t)pos_ev->position;
            key_evt[1] = pos_ev->state ? 1 : 0;
            send_packet(EVT_KEY_TEST, 0, key_evt, 2);
        }

        if (!pos_ev->state) {
            return 0; // key released
        }

        // Physical Presence Unlock: Index 40 is 'Z' key (Row 4, Col 1)
        if (pos_ev->position == UNLOCK_KEY_POSITION &&
            (zmk_keymap_layer_active(FN_LAYER_INDEX) || zmk_keymap_layer_active(TRI_LAYER_INDEX))) {
            preonic_studio_unlock();
#if IS_ENABLED(CONFIG_KEYBOARDIO_PREONIC_SOUND)
            preonic_sound_play_studio_unlock();
#endif
#if IS_ENABLED(CONFIG_KEYBOARDIO_BUTTERFLY_STATUS)
            butterfly_show_studio_unlock();
#endif
            uint8_t unlocked_by = 1; // physical Fn+Z
            send_packet(EVT_UNLOCKED, 0, &unlocked_by, 1);
            return 0;
        }
    }

    const struct zmk_layer_state_changed *layer_ev = as_zmk_layer_state_changed(eh);
    if (layer_ev != NULL) {
        if (was_dtr_active) {
            uint8_t active_layer = (uint8_t)zmk_keymap_highest_layer_active();
            send_packet(EVT_LAYER_CHANGED, 0, &active_layer, 1);
        }
        return 0;
    }

    struct zmk_activity_state_changed *act_ev = as_zmk_activity_state_changed(eh);
    if (act_ev != NULL) {
        if (act_ev->state == ZMK_ACTIVITY_SLEEP) {
            if (!preonic_studio_is_locked()) {
                preonic_studio_lock();
                uint8_t reason = 0x01; // sleep/timeout
                send_packet(EVT_LOCKED, 0, &reason, 1);
            }
        }
    }

    return 0;
}

ZMK_LISTENER(preonic_studio, preonic_studio_event_listener);
ZMK_SUBSCRIPTION(preonic_studio, zmk_position_state_changed);
ZMK_SUBSCRIPTION(preonic_studio, zmk_activity_state_changed);
ZMK_SUBSCRIPTION(preonic_studio, zmk_layer_state_changed);

#if IS_ENABLED(CONFIG_SETTINGS)
static int studio_settings_set(const char *name, size_t len, settings_read_cb read_cb, void *cb_arg) {
    const char *next;
    if (settings_name_steq(name, "knob", &next) && next) {
        char *endptr;
        unsigned long layer = strtoul(next, &endptr, 10);
        if (*endptr == '\0' && layer < NUM_LAYERS) {
            read_cb(cb_arg, &knob_configs[layer], MIN(len, sizeof(struct studio_knob_config)));
        }
        return 0;
    }
    if (settings_name_steq(name, "mouse", &next) && !next) {
        read_cb(cb_arg, &mouse_cfg, MIN(len, sizeof(struct studio_mouse_config)));
        return 0;
    }
    if (settings_name_steq(name, "audio", &next) && !next) {
        read_cb(cb_arg, &audio_cfg, MIN(len, sizeof(struct studio_audio_config)));
        return 0;
    }
    return -ENOENT;
}

static struct settings_handler studio_settings_conf = {
    .name = "studio",
    .h_set = studio_settings_set,
};
#endif

void preonic_studio_init(void) {
    ring_buf_init(&rx_ringbuf, sizeof(rx_buffer), rx_buffer);
    k_mutex_init(&tx_mutex);
    k_work_init(&process_work, process_work_handler);
    k_work_init_delayable(&auto_lock_work, auto_lock_work_handler);

#if IS_ENABLED(CONFIG_SETTINGS)
    settings_register(&studio_settings_conf);
    settings_load_subtree("studio");
#endif

    if (uart_dev && device_is_ready(uart_dev)) {
        uart_irq_callback_user_data_set(uart_dev, uart_cb, NULL);
        uart_irq_rx_enable(uart_dev);
        LOG_INF("Preonic Studio CDC ACM UART initialized");
    } else {
        LOG_WRN("Preonic Studio CDC ACM UART device not ready");
    }
}

static int preonic_studio_sys_init(void) {
    preonic_studio_init();
    return 0;
}

SYS_INIT(preonic_studio_sys_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
