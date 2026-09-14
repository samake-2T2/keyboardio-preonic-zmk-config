/*
 * Copyright (c) 2026 Keyboardio Preonic Custom Firmware
 * SPDX-License-Identifier: MIT
 */

#include <zephyr/kernel.h>
#include <zephyr/init.h>
#include <zephyr/logging/log.h>
#include <zephyr/random/random.h>
#include <string.h>

#if IS_ENABLED(CONFIG_SETTINGS)
#include <zephyr/settings/settings.h>
#endif

#include <dt-bindings/zmk/keys.h>
#include <dt-bindings/zmk/modifiers.h>
#include <dt-bindings/zmk/hid_usage.h>
#include <dt-bindings/zmk/hid_usage_pages.h>
#include <zmk/hid.h>
#include <zmk/keymap.h>
#include <zmk/event_manager.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/events/sensor_event.h>
#include <zmk/events/activity_state_changed.h>
#include <zmk/events/keycode_state_changed.h>

#include "password_generator.h"
#include "butterfly_status.h"
#include "preonic_sound.h"

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#define KNOB_SWITCH_POSITION 2
#define FN_LAYER_INDEX 3
#define TRI_LAYER_INDEX 4

#define TYPING_STEP_INTERVAL_MS 12

static const uint8_t ALLOWED_LENGTHS[] = { 12, 16, 20, 24 };
#define DEFAULT_LENGTH_INDEX 1 // 16 characters

static uint8_t current_length_idx = DEFAULT_LENGTH_INDEX;

#define ENCODER_PULSES_PER_DETENT 8
#define ENCODER_RESET_TIMEOUT_MS 350
#define ENCODER_MIN_STEP_INTERVAL_MS 100

static int8_t pulse_accumulator = 0;
static int64_t last_pulse_time = 0;
static int64_t last_step_time = 0;

struct pw_step {
    uint32_t keycode;
    bool pressed;
};

#define MAX_PW_STEPS 64
static struct pw_step steps[MAX_PW_STEPS];
static size_t num_steps = 0;
static size_t current_step = 0;
static bool typing_in_progress = false;

static struct k_work_delayable pw_type_work;

static const char UPPER_SET[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char LOWER_SET[] = "abcdefghijklmnopqrstuvwxyz";
static const char DIGIT_SET[] = "0123456789";
static const char DB_SAFE_SPECIALS[] = "_-";
static const char WEB_SPECIALS[] = "_-@.";

static const uint32_t letter_keys[26] = {
    A, B, C, D, E, F, G, H, I, J, K, L, M,
    N, O, P, Q, R, S, T, U, V, W, X, Y, Z
};

static const uint32_t digit_keys[10] = {
    N0, N1, N2, N3, N4, N5, N6, N7, N8, N9
};

#if IS_ENABLED(CONFIG_SETTINGS)
static int pw_settings_set(const char *name, size_t len, settings_read_cb read_cb, void *cb_arg) {
    const char *next;
    if (settings_name_steq(name, "len_idx", &next) && !next) {
        uint8_t val = 0;
        if (len <= sizeof(val)) {
            read_cb(cb_arg, &val, len);
            if (val < ARRAY_SIZE(ALLOWED_LENGTHS)) {
                current_length_idx = val;
                LOG_INF("Loaded password length from flash: %u", ALLOWED_LENGTHS[current_length_idx]);
            }
        }
        return 0;
    }
    return -ENOENT;
}

struct settings_handler pw_settings_conf = {
    .name = "pw_gen",
    .h_set = pw_settings_set,
};
#endif

static void get_random_bytes(uint8_t *buf, size_t len) {
    if (sys_csrand_get(buf, len) != 0) {
        sys_rand_get(buf, len);
    }
}

static void generate_password_string(char *out, uint8_t length, enum password_mode mode) {
    const char *specials = (mode == PW_MODE_WEB_EXTENDED) ? WEB_SPECIALS : DB_SAFE_SPECIALS;
    size_t specials_len = (mode == PW_MODE_WEB_EXTENDED) ? (sizeof(WEB_SPECIALS) - 1) : (sizeof(DB_SAFE_SPECIALS) - 1);

    size_t idx = 0;
    uint8_t rand_byte;

    // 1. Ensure at least 1 uppercase
    get_random_bytes(&rand_byte, 1);
    out[idx++] = UPPER_SET[rand_byte % 26];

    // 2. Ensure at least 1 lowercase
    get_random_bytes(&rand_byte, 1);
    out[idx++] = LOWER_SET[rand_byte % 26];

    // 3. Ensure at least 1 digit
    get_random_bytes(&rand_byte, 1);
    out[idx++] = DIGIT_SET[rand_byte % 10];

    // 4. Ensure at least 1 special char if not alphanumeric mode
    if (mode != PW_MODE_ALPHANUMERIC && specials_len > 0) {
        get_random_bytes(&rand_byte, 1);
        out[idx++] = specials[rand_byte % specials_len];
    }

    // 5. Build combined pool for remaining characters
    char pool[70];
    size_t pool_len = 0;
    memcpy(pool + pool_len, UPPER_SET, 26); pool_len += 26;
    memcpy(pool + pool_len, LOWER_SET, 26); pool_len += 26;
    memcpy(pool + pool_len, DIGIT_SET, 10); pool_len += 10;
    if (mode != PW_MODE_ALPHANUMERIC && specials_len > 0) {
        memcpy(pool + pool_len, specials, specials_len); pool_len += specials_len;
    }

    while (idx < length) {
        get_random_bytes(&rand_byte, 1);
        out[idx++] = pool[rand_byte % pool_len];
    }

    // 6. Cryptographic Fisher-Yates shuffle
    for (int i = length - 1; i > 0; i--) {
        get_random_bytes(&rand_byte, 1);
        int j = rand_byte % (i + 1);
        char tmp = out[i];
        out[i] = out[j];
        out[j] = tmp;
    }
    out[length] = '\0';
}

static uint32_t char_to_keycode(char c) {
    if (c >= 'a' && c <= 'z') {
        return letter_keys[c - 'a'];
    }
    if (c >= 'A' && c <= 'Z') {
        return LS(letter_keys[c - 'A']);
    }
    if (c >= '0' && c <= '9') {
        return digit_keys[c - '0'];
    }
    if (c == '-') {
        return MINUS;
    }
    if (c == '_') {
        return UNDER;
    }
    if (c == '.') {
        return PERIOD;
    }
    if (c == '@') {
        return AT;
    }
    return 0;
}

static void pw_type_work_handler(struct k_work *work) {
    ARG_UNUSED(work);

    if (!typing_in_progress) {
        return;
    }

    if (current_step < num_steps) {
        struct pw_step step = steps[current_step++];
        raise_zmk_keycode_state_changed_from_encoded(step.keycode, step.pressed, k_uptime_get());
        k_work_reschedule(&pw_type_work, K_MSEC(TYPING_STEP_INTERVAL_MS));
    } else {
        typing_in_progress = false;
        zmk_hid_masked_modifiers_clear();
        num_steps = 0;
        current_step = 0;
        butterfly_show_password_success();
        preonic_sound_play_coin();
    }
}

void password_generator_cycle_length(int direction) {
    uint8_t old_idx = current_length_idx;

    if (direction > 0) {
        if (current_length_idx < ARRAY_SIZE(ALLOWED_LENGTHS) - 1) {
            current_length_idx++;
        }
    } else if (direction < 0) {
        if (current_length_idx > 0) {
            current_length_idx--;
        }
    }

    if (current_length_idx == old_idx) {
        return;
    }

    uint8_t len = ALLOWED_LENGTHS[current_length_idx];
    LOG_INF("Password length set to %u characters", len);

    static const uint32_t TONES[] = { 523, 659, 784, 1046 }; // C5, E5, G5, C6
    preonic_sound_play_tone(TONES[current_length_idx], 35);

    butterfly_show_password_length(len);

#if IS_ENABLED(CONFIG_SETTINGS)
    settings_save_one("pw_gen/len_idx", &current_length_idx, sizeof(current_length_idx));
#endif
}

uint8_t password_generator_get_length(void) {
    return ALLOWED_LENGTHS[current_length_idx];
}

bool password_generator_is_typing(void) {
    return typing_in_progress;
}

void password_generator_trigger(enum password_mode mode) {
    if (typing_in_progress) {
        return;
    }

    uint8_t len = ALLOWED_LENGTHS[current_length_idx];
    char pw_str[32];
    generate_password_string(pw_str, len, mode);
    LOG_INF("Generating password (len=%u, mode=%d)", len, mode);

    num_steps = 0;
    current_step = 0;

    for (uint8_t i = 0; i < len && i < sizeof(pw_str); i++) {
        uint32_t kc = char_to_keycode(pw_str[i]);
        if (kc != 0 && num_steps + 2 <= MAX_PW_STEPS) {
            steps[num_steps++] = (struct pw_step){ .keycode = kc, .pressed = true };
            steps[num_steps++] = (struct pw_step){ .keycode = kc, .pressed = false };
        }
    }

    typing_in_progress = true;
    zmk_hid_masked_modifiers_set(zmk_hid_get_explicit_mods());
    k_work_reschedule(&pw_type_work, K_MSEC(40));
}

static int password_generator_event_listener(const zmk_event_t *eh) {
    const struct zmk_activity_state_changed *act_ev = as_zmk_activity_state_changed(eh);
    if (act_ev != NULL && act_ev->state == ZMK_ACTIVITY_SLEEP) {
        if (typing_in_progress) {
            k_work_cancel_delayable(&pw_type_work);
            typing_in_progress = false;
            zmk_hid_masked_modifiers_clear();
        }
        return 0;
    }

    const struct zmk_position_state_changed *pos_ev = as_zmk_position_state_changed(eh);
    if (pos_ev != NULL && pos_ev->position == KNOB_SWITCH_POSITION) {
        if (zmk_keymap_layer_active(FN_LAYER_INDEX) || zmk_keymap_layer_active(TRI_LAYER_INDEX)) {
            if (pos_ev->state) {
                // Knob pressed on Fn layer
                zmk_mod_flags_t mods = zmk_hid_get_explicit_mods();
                enum password_mode mode;
                if (mods & (MOD_LSFT | MOD_RSFT)) {
                    mode = PW_MODE_WEB_EXTENDED;
                } else if (mods & (MOD_LCTL | MOD_RCTL)) {
                    mode = PW_MODE_ALPHANUMERIC;
                } else {
                    mode = PW_MODE_DB_SAFE;
                }
                password_generator_trigger(mode);
            }
            return ZMK_EV_EVENT_HANDLED;
        }
    }

    const struct zmk_sensor_event *sev = as_zmk_sensor_event(eh);
    if (sev != NULL) {
        if (zmk_keymap_layer_active(FN_LAYER_INDEX) || zmk_keymap_layer_active(TRI_LAYER_INDEX)) {
            if (sev->channel_data_size > 0) {
                int val = sev->channel_data[0].value.val1;
                int64_t now = k_uptime_get();

                // Reset accumulator if idle for > 300ms
                if (now - last_pulse_time > ENCODER_RESET_TIMEOUT_MS) {
                    pulse_accumulator = 0;
                }
                last_pulse_time = now;

                // Reset on direction change for instant reverse response
                if ((pulse_accumulator > 0 && val < 0) || (pulse_accumulator < 0 && val > 0)) {
                    pulse_accumulator = 0;
                }

                pulse_accumulator += val;

                if (pulse_accumulator >= ENCODER_PULSES_PER_DETENT) {
                    if (now - last_step_time >= ENCODER_MIN_STEP_INTERVAL_MS) {
                        password_generator_cycle_length(1);
                        last_step_time = now;
                        pulse_accumulator = 0;
                    }
                } else if (pulse_accumulator <= -ENCODER_PULSES_PER_DETENT) {
                    if (now - last_step_time >= ENCODER_MIN_STEP_INTERVAL_MS) {
                        password_generator_cycle_length(-1);
                        last_step_time = now;
                        pulse_accumulator = 0;
                    }
                }
                return ZMK_EV_EVENT_HANDLED;
            }
        } else {
            pulse_accumulator = 0;
        }
    }

    return 0;
}

ZMK_LISTENER(password_generator, password_generator_event_listener);
ZMK_SUBSCRIPTION(password_generator, zmk_position_state_changed);
ZMK_SUBSCRIPTION(password_generator, zmk_sensor_event);
ZMK_SUBSCRIPTION(password_generator, zmk_activity_state_changed);

static int password_generator_init(void) {
    k_work_init_delayable(&pw_type_work, pw_type_work_handler);
#if IS_ENABLED(CONFIG_SETTINGS)
    settings_register(&pw_settings_conf);
#endif
    return 0;
}

SYS_INIT(password_generator_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
