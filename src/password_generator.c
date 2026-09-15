/*
 * Copyright (c) 2026 Keyboardio Preonic Custom Firmware
 * SPDX-License-Identifier: MIT
 */

#include <zephyr/kernel.h>
#include <zephyr/init.h>
#include <zephyr/logging/log.h>
#include <zephyr/random/random.h>
#include <string.h>
#include <errno.h>

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
#define W_KEY_POSITION 17
#define A_KEY_POSITION 28
#define D_KEY_POSITION 30
#define FN_LAYER_INDEX 3
#define TRI_LAYER_INDEX 4

#define PW_MAX_SPECIALS 32

static uint8_t default_length = 16;
static uint8_t typing_interval_ms = 12;
static char custom_specials[PW_MAX_SPECIALS + 1] = "!@#$%*?_-.@";
static uint8_t custom_specials_len = 11;

#define KNOB_LONG_PRESS_MS 400
#define KNOB_DOUBLE_CLICK_MS 250

static struct k_work_delayable knob_long_press_work;
static struct k_work_delayable knob_click_work;
static bool knob_long_press_triggered = false;
static uint8_t knob_click_count = 0;

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

#define MAX_PW_STEPS 128
static struct pw_step steps[MAX_PW_STEPS];

static size_t num_steps = 0;
static size_t current_step = 0;
static bool typing_in_progress = false;

static struct k_work_delayable pw_type_work;

static const char UPPER_SET[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char LOWER_SET[] = "abcdefghijklmnopqrstuvwxyz";
static const char DIGIT_SET[] = "0123456789";
static const char DB_SAFE_SPECIALS[] = "_-";

static const uint32_t letter_keys[26] = {
    A, B, C, D, E, F, G, H, I, J, K, L, M,
    N, O, P, Q, R, S, T, U, V, W, X, Y, Z
};

static const uint32_t digit_keys[10] = {
    N0, N1, N2, N3, N4, N5, N6, N7, N8, N9
};

struct __packed pw_gen_config_persisted {
    uint8_t default_len;
    uint8_t interval_ms;
    uint8_t specials_len;
    char specials[PW_MAX_SPECIALS];
};

#if IS_ENABLED(CONFIG_SETTINGS)
static int pw_settings_set(const char *name, size_t len, settings_read_cb read_cb, void *cb_arg) {
    const char *next;
    if (settings_name_steq(name, "config", &next) && !next) {
        struct pw_gen_config_persisted cfg;
        if (len <= sizeof(cfg)) {
            read_cb(cb_arg, &cfg, len);
            if (cfg.default_len >= 8 && cfg.default_len <= 32) {
                default_length = cfg.default_len;
                for (uint8_t i = 0; i < ARRAY_SIZE(ALLOWED_LENGTHS); i++) {
                    if (ALLOWED_LENGTHS[i] == default_length) {
                        current_length_idx = i;
                        break;
                    }
                }
            }
            if (cfg.interval_ms >= 5 && cfg.interval_ms <= 50) {
                typing_interval_ms = cfg.interval_ms;
            }
            if (cfg.specials_len <= PW_MAX_SPECIALS) {
                custom_specials_len = cfg.specials_len;
                memcpy(custom_specials, cfg.specials, custom_specials_len);
                custom_specials[custom_specials_len] = '\0';
            }
            LOG_INF("Loaded password config from flash: len=%u, interval=%ums, specials=%.*s",
                    default_length, typing_interval_ms, custom_specials_len, custom_specials);
        }
        return 0;
    }
    if (settings_name_steq(name, "len_idx", &next) && !next) {
        uint8_t val = 0;
        if (len <= sizeof(val)) {
            read_cb(cb_arg, &val, len);
            if (val < ARRAY_SIZE(ALLOWED_LENGTHS)) {
                current_length_idx = val;
                default_length = ALLOWED_LENGTHS[current_length_idx];
                LOG_INF("Loaded password length from flash: %u", default_length);
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
    const char *specials = (mode == PW_MODE_WEB_EXTENDED) ?
                           (custom_specials_len > 0 ? custom_specials : DB_SAFE_SPECIALS) :
                           DB_SAFE_SPECIALS;
    size_t specials_len = (mode == PW_MODE_WEB_EXTENDED) ?
                          (custom_specials_len > 0 ? custom_specials_len : (sizeof(DB_SAFE_SPECIALS) - 1)) :
                          (sizeof(DB_SAFE_SPECIALS) - 1);

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
    char pool[128];
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
    if (c == '-') return MINUS;
    if (c == '_') return UNDER;
    if (c == '.') return PERIOD;
    if (c == '@') return AT;
    if (c == '!') return LS(N1);
    if (c == '#') return LS(N3);
    if (c == '$') return LS(N4);
    if (c == '%') return LS(N5);
    if (c == '^') return LS(N6);
    if (c == '&') return LS(N7);
    if (c == '*') return LS(N8);
    if (c == '(') return LS(N9);
    if (c == ')') return LS(N0);
    if (c == '+') return LS(EQUAL);
    if (c == '=') return EQUAL;
    if (c == '{') return LS(LBKT);
    if (c == '}') return LS(RBKT);
    if (c == '[') return LBKT;
    if (c == ']') return RBKT;
    if (c == '|') return LS(BACKSLASH);
    if (c == '\\') return BACKSLASH;
    if (c == ':') return LS(SEMI);
    if (c == ';') return SEMI;
    if (c == '\'') return SQT;
    if (c == '"') return LS(SQT);
    if (c == '<') return LS(COMMA);
    if (c == '>') return LS(PERIOD);
    if (c == '?') return LS(SLASH);
    if (c == '/') return SLASH;
    if (c == '~') return LS(GRAVE);
    if (c == '`') return GRAVE;
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
        k_work_reschedule(&pw_type_work, K_MSEC(typing_interval_ms));
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

    default_length = ALLOWED_LENGTHS[current_length_idx];
    LOG_INF("Password length set to %u characters", default_length);

    static const uint32_t TONES[] = { 523, 659, 784, 1046 }; // C5, E5, G5, C6
    preonic_sound_play_tone(TONES[current_length_idx], 35);

    butterfly_show_password_length(default_length);

#if IS_ENABLED(CONFIG_SETTINGS)
    struct pw_gen_config_persisted cfg = {
        .default_len = default_length,
        .interval_ms = typing_interval_ms,
        .specials_len = custom_specials_len,
    };
    memset(cfg.specials, 0, sizeof(cfg.specials));
    memcpy(cfg.specials, custom_specials, custom_specials_len);
    settings_save_one("pw_gen/config", &cfg, sizeof(cfg));
    settings_save_one("pw_gen/len_idx", &current_length_idx, sizeof(current_length_idx));
#endif
}

uint8_t password_generator_get_length(void) {
    return default_length;
}

bool password_generator_is_typing(void) {
    return typing_in_progress;
}

void password_generator_get_config(uint8_t *default_len, uint8_t *interval_ms, char *specials, uint8_t *specials_len) {
    if (default_len) {
        *default_len = default_length;
    }
    if (interval_ms) {
        *interval_ms = typing_interval_ms;
    }
    if (specials_len) {
        *specials_len = custom_specials_len;
    }
    if (specials) {
        memcpy(specials, custom_specials, custom_specials_len);
        if (custom_specials_len < PW_MAX_SPECIALS) {
            memset(specials + custom_specials_len, 0, PW_MAX_SPECIALS - custom_specials_len);
        }
    }
}

int password_generator_set_config(uint8_t default_len, uint8_t interval_ms, const char *specials, uint8_t specials_len) {
    if (default_len < 8 || default_len > 32) {
        return -EINVAL;
    }
    if (interval_ms < 5 || interval_ms > 50) {
        return -EINVAL;
    }
    if (specials_len > PW_MAX_SPECIALS) {
        return -EINVAL;
    }
    if (specials_len > 0 && specials == NULL) {
        return -EINVAL;
    }

    default_length = default_len;
    typing_interval_ms = interval_ms;

    for (uint8_t i = 0; i < ARRAY_SIZE(ALLOWED_LENGTHS); i++) {
        if (ALLOWED_LENGTHS[i] == default_length) {
            current_length_idx = i;
            break;
        }
    }

    if (specials && specials_len > 0) {
        memcpy(custom_specials, specials, specials_len);
        custom_specials[specials_len] = '\0';
        custom_specials_len = specials_len;
    } else {
        custom_specials_len = 0;
        custom_specials[0] = '\0';
    }

#if IS_ENABLED(CONFIG_SETTINGS)
    struct pw_gen_config_persisted cfg = {
        .default_len = default_length,
        .interval_ms = typing_interval_ms,
        .specials_len = custom_specials_len,
    };
    memset(cfg.specials, 0, sizeof(cfg.specials));
    memcpy(cfg.specials, custom_specials, custom_specials_len);
    settings_save_one("pw_gen/config", &cfg, sizeof(cfg));
    settings_save_one("pw_gen/len_idx", &current_length_idx, sizeof(current_length_idx));
    LOG_INF("Saved password config to flash: len=%u, interval=%ums, specials=%.*s",
            default_length, typing_interval_ms, custom_specials_len, custom_specials);
#endif

    return 0;
}

void password_generator_trigger(enum password_mode mode) {
    if (typing_in_progress) {
        return;
    }

    uint8_t len = default_length;
    char pw_str[64];
    if (len > sizeof(pw_str) - 1) {
        len = sizeof(pw_str) - 1;
    }
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


static void knob_long_press_work_handler(struct k_work *work) {
    ARG_UNUSED(work);
    knob_long_press_triggered = true;
    knob_click_count = 0;
    LOG_INF("Knob long press detected -> Alphanumeric mode");
    preonic_sound_play_tone(880, 50);
    password_generator_trigger(PW_MODE_ALPHANUMERIC);
}

static void knob_click_work_handler(struct k_work *work) {
    ARG_UNUSED(work);
    knob_click_count = 0;
    LOG_INF("Knob single click detected -> DB Safe mode");
    password_generator_trigger(PW_MODE_DB_SAFE);
}

static int password_generator_event_listener(const zmk_event_t *eh) {
    const struct zmk_activity_state_changed *act_ev = as_zmk_activity_state_changed(eh);
    if (act_ev != NULL && act_ev->state == ZMK_ACTIVITY_SLEEP) {
        if (typing_in_progress) {
            k_work_cancel_delayable(&pw_type_work);
            typing_in_progress = false;
            zmk_hid_masked_modifiers_clear();
        }
        k_work_cancel_delayable(&knob_long_press_work);
        k_work_cancel_delayable(&knob_click_work);
        knob_click_count = 0;
        knob_long_press_triggered = false;
        return 0;
    }

    const struct zmk_position_state_changed *pos_ev = as_zmk_position_state_changed(eh);
    if (pos_ev != NULL) {
        if (zmk_keymap_layer_active(FN_LAYER_INDEX) || zmk_keymap_layer_active(TRI_LAYER_INDEX)) {
            // 1. Direct Mnemonic Keys (D, W, A)
            if (pos_ev->position == D_KEY_POSITION) {
                if (pos_ev->state) {
                    LOG_INF("Fn + D pressed -> DB Safe mode");
                    password_generator_trigger(PW_MODE_DB_SAFE);
                }
                return ZMK_EV_EVENT_HANDLED;
            } else if (pos_ev->position == W_KEY_POSITION) {
                if (pos_ev->state) {
                    LOG_INF("Fn + W pressed -> Web Extended mode");
                    password_generator_trigger(PW_MODE_WEB_EXTENDED);
                }
                return ZMK_EV_EVENT_HANDLED;
            } else if (pos_ev->position == A_KEY_POSITION) {
                if (pos_ev->state) {
                    LOG_INF("Fn + A pressed -> Alphanumeric mode");
                    password_generator_trigger(PW_MODE_ALPHANUMERIC);
                }
                return ZMK_EV_EVENT_HANDLED;
            }

            // 2. Knob Push Switch (Position 2)
            if (pos_ev->position == KNOB_SWITCH_POSITION) {
                if (pos_ev->state) {
                    // Pressed down: start long-press timer
                    knob_long_press_triggered = false;
                    k_work_reschedule(&knob_long_press_work, K_MSEC(KNOB_LONG_PRESS_MS));
                } else {
                    // Released
                    k_work_cancel_delayable(&knob_long_press_work);
                    if (knob_long_press_triggered) {
                        knob_long_press_triggered = false;
                        knob_click_count = 0;
                        return ZMK_EV_EVENT_HANDLED;
                    }

                    knob_click_count++;
                    if (knob_click_count == 1) {
                        k_work_reschedule(&knob_click_work, K_MSEC(KNOB_DOUBLE_CLICK_MS));
                    } else if (knob_click_count >= 2) {
                        k_work_cancel_delayable(&knob_click_work);
                        knob_click_count = 0;
                        LOG_INF("Knob double click detected -> Web Extended mode");
                        password_generator_trigger(PW_MODE_WEB_EXTENDED);
                    }
                }
                return ZMK_EV_EVENT_HANDLED;
            }
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
    k_work_init_delayable(&knob_long_press_work, knob_long_press_work_handler);
    k_work_init_delayable(&knob_click_work, knob_click_work_handler);
#if IS_ENABLED(CONFIG_SETTINGS)
    settings_register(&pw_settings_conf);
#endif
    return 0;
}

SYS_INIT(password_generator_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
