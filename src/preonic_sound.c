/*
 * Copyright (c) 2026 Keyboardio Preonic Custom Firmware
 * SPDX-License-Identifier: MIT
 */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/pwm.h>
#include <zephyr/init.h>
#include <zephyr/logging/log.h>

#if defined(CONFIG_SOC_FAMILY_NRF) || defined(NRF52840_XXAA) || defined(NRF_POWER)
#include <helpers/nrfx_reset_reason.h>
#include <hal/nrf_power.h>
#endif

#include <zmk/activity.h>
#include <zmk/event_manager.h>
#include <zmk/events/activity_state_changed.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/keymap.h>

#include "preonic_sound.h"

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#if DT_NODE_HAS_STATUS(DT_NODELABEL(pwm0), okay)
#define PWM_DEV_NODE DT_NODELABEL(pwm0)
#else
#error "pwm0 devicetree node not found or not enabled"
#endif

#define SPEAKER_PWM_CHANNEL 0

// Keymap indices for Fn toggles
#define FN_LAYER_INDEX 3
#define TRI_LAYER_INDEX 4
#define S_KEY_POSITION 29
#define C_KEY_POSITION 42

enum sound_state {
    SOUND_STATE_IDLE = 0,
    SOUND_STATE_CLICKY,
    SOUND_STATE_TOGGLE_TONE,
    SOUND_STATE_COIN_B5,
    SOUND_STATE_COIN_E6,
    SOUND_STATE_LOW_BATT_1,
    SOUND_STATE_LOW_BATT_PAUSE,
    SOUND_STATE_LOW_BATT_2,
    SOUND_STATE_CUSTOM_TONE,
};

static const struct device *const pwm_dev = DEVICE_DT_GET(PWM_DEV_NODE);

static enum sound_state current_sound_state = SOUND_STATE_IDLE;
static struct k_work_delayable sound_work;
static struct k_work_delayable boot_coin_work;

static bool sound_master_enabled = IS_ENABLED(CONFIG_PREONIC_SOUND_MASTER_DEFAULT);
static bool clicky_enabled = IS_ENABLED(CONFIG_PREONIC_SOUND_CLICKY_DEFAULT);
static bool cold_boot_done = false;

#if defined(NRF_POWER)
#define GPREGRET_MAGIC_MASK  0xF0
#define GPREGRET_MAGIC_VAL   0x50 // Magic tag 'S' (Sound)
#define GPREGRET_SOUND_BIT   (1U << 0)
#define GPREGRET_CLICKY_BIT  (1U << 1)

static void save_sound_state(void) {
    uint8_t val = GPREGRET_MAGIC_VAL;
    if (sound_master_enabled) {
        val |= GPREGRET_SOUND_BIT;
    }
    if (clicky_enabled) {
        val |= GPREGRET_CLICKY_BIT;
    }
    nrf_power_gpregret_set(NRF_POWER, 1, val);
}

static void load_sound_state(void) {
    uint32_t reg = nrf_power_gpregret_get(NRF_POWER, 1);
    if ((reg & GPREGRET_MAGIC_MASK) == GPREGRET_MAGIC_VAL) {
        sound_master_enabled = (reg & GPREGRET_SOUND_BIT) != 0;
        clicky_enabled = (reg & GPREGRET_CLICKY_BIT) != 0;
    } else {
        sound_master_enabled = IS_ENABLED(CONFIG_PREONIC_SOUND_MASTER_DEFAULT);
        clicky_enabled = IS_ENABLED(CONFIG_PREONIC_SOUND_CLICKY_DEFAULT);
        save_sound_state();
    }
}

static inline bool is_wake_from_system_off(void) {
    uint32_t reason = nrfx_reset_reason_get();
    return (reason & (NRFX_RESET_REASON_OFF_MASK
#if NRFX_RESET_REASON_HAS_LPCOMP
                    | NRFX_RESET_REASON_LPCOMP_MASK
#endif
#if NRFX_RESET_REASON_HAS_NFC
                    | NRFX_RESET_REASON_NFC_MASK
#endif
           )) != 0;
}
#else
static inline void save_sound_state(void) {}
static inline void load_sound_state(void) {
    sound_master_enabled = IS_ENABLED(CONFIG_PREONIC_SOUND_MASTER_DEFAULT);
    clicky_enabled = IS_ENABLED(CONFIG_PREONIC_SOUND_CLICKY_DEFAULT);
}
static inline bool is_wake_from_system_off(void) {
    return false;
}
#endif

static inline int set_tone(uint32_t freq_hz) {
    if (!device_is_ready(pwm_dev)) {
        return -ENODEV;
    }
    if (freq_hz == 0) {
        return pwm_set(pwm_dev, SPEAKER_PWM_CHANNEL, 0, 0, 0);
    }
    uint32_t period_ns = 1000000000U / freq_hz;
    uint32_t pulse_ns = period_ns / 2;
    return pwm_set(pwm_dev, SPEAKER_PWM_CHANNEL, period_ns, pulse_ns, 0);
}

static void sound_work_handler(struct k_work *work) {
    ARG_UNUSED(work);

    switch (current_sound_state) {
    case SOUND_STATE_COIN_B5:
        // Transition to 2nd note of Mario Coin: E6 (1319Hz) for 350ms
        current_sound_state = SOUND_STATE_COIN_E6;
        set_tone(1319);
        k_work_reschedule(&sound_work, K_MSEC(350));
        break;

    case SOUND_STATE_LOW_BATT_1:
        // Pause between beeps (80ms)
        current_sound_state = SOUND_STATE_LOW_BATT_PAUSE;
        set_tone(0);
        k_work_reschedule(&sound_work, K_MSEC(80));
        break;

    case SOUND_STATE_LOW_BATT_PAUSE:
        // 2nd beep: 1500Hz for 100ms
        current_sound_state = SOUND_STATE_LOW_BATT_2;
        set_tone(1500);
        k_work_reschedule(&sound_work, K_MSEC(100));
        break;

    case SOUND_STATE_LOW_BATT_2:
    case SOUND_STATE_COIN_E6:
    case SOUND_STATE_CLICKY:
    case SOUND_STATE_TOGGLE_TONE:
    case SOUND_STATE_CUSTOM_TONE:
    default:
        set_tone(0);
        current_sound_state = SOUND_STATE_IDLE;
        break;
    }
}

void preonic_sound_stop(void) {
    k_work_cancel_delayable(&sound_work);
    k_work_cancel_delayable(&boot_coin_work);
    current_sound_state = SOUND_STATE_IDLE;
    set_tone(0);
}

void preonic_sound_play_tone(uint32_t freq_hz, uint32_t duration_ms) {
    if (!sound_master_enabled || !device_is_ready(pwm_dev)) {
        return;
    }
    if (freq_hz == 0 || duration_ms == 0) {
        preonic_sound_stop();
        return;
    }
    current_sound_state = SOUND_STATE_CUSTOM_TONE;
    set_tone(freq_hz);
    k_work_reschedule(&sound_work, K_MSEC(duration_ms));
}

void preonic_sound_play_coin(void) {
    if (!sound_master_enabled || !device_is_ready(pwm_dev)) {
        return;
    }
    // 1st note of Mario Coin: B5 (988Hz) for 65ms
    current_sound_state = SOUND_STATE_COIN_B5;
    set_tone(988);
    k_work_reschedule(&sound_work, K_MSEC(65));
}

void preonic_sound_play_low_battery_warning(void) {
    if (!sound_master_enabled || !device_is_ready(pwm_dev)) {
        return;
    }
    // 1st beep: 1500Hz for 100ms
    current_sound_state = SOUND_STATE_LOW_BATT_1;
    set_tone(1500);
    k_work_reschedule(&sound_work, K_MSEC(100));
}

void preonic_sound_play_click(void) {
    if (!sound_master_enabled || !clicky_enabled || !device_is_ready(pwm_dev)) {
        return;
    }
    // Do not interrupt Mario Coin or Low Battery warning sequence
    if (current_sound_state == SOUND_STATE_COIN_B5 || current_sound_state == SOUND_STATE_COIN_E6 ||
        current_sound_state == SOUND_STATE_LOW_BATT_1 || current_sound_state == SOUND_STATE_LOW_BATT_PAUSE ||
        current_sound_state == SOUND_STATE_LOW_BATT_2) {
        return;
    }
    current_sound_state = SOUND_STATE_CLICKY;
    set_tone(CONFIG_PREONIC_SOUND_CLICK_FREQ);
    k_work_reschedule(&sound_work, K_MSEC(CONFIG_PREONIC_SOUND_CLICK_DURATION_MS));
}

bool preonic_sound_toggle_master(void) {
    sound_master_enabled = !sound_master_enabled;
    save_sound_state();

    if (!device_is_ready(pwm_dev)) {
        return sound_master_enabled;
    }

    current_sound_state = SOUND_STATE_TOGGLE_TONE;
    if (sound_master_enabled) {
        // High confirmation tone for ON (2200Hz, 80ms)
        set_tone(2200);
    } else {
        // Low confirmation tone for OFF (1000Hz, 60ms)
        set_tone(1000);
    }
    k_work_reschedule(&sound_work, K_MSEC(sound_master_enabled ? 80 : 60));

    LOG_INF("Preonic master sound toggled: %s", sound_master_enabled ? "ON" : "OFF");
    return sound_master_enabled;
}

bool preonic_sound_is_master_enabled(void) {
    return sound_master_enabled;
}

bool preonic_sound_toggle_clicky(void) {
    clicky_enabled = !clicky_enabled;
    save_sound_state();

    if (!sound_master_enabled || !device_is_ready(pwm_dev)) {
        return clicky_enabled;
    }

    current_sound_state = SOUND_STATE_TOGGLE_TONE;
    if (clicky_enabled) {
        // High confirmation tone for ON (2400Hz, 50ms)
        set_tone(2400);
    } else {
        // Low confirmation tone for OFF (1200Hz, 50ms)
        set_tone(1200);
    }
    k_work_reschedule(&sound_work, K_MSEC(50));

    LOG_INF("Preonic Audio Clicky toggled: %s", clicky_enabled ? "ON" : "OFF");
    return clicky_enabled;
}

bool preonic_sound_is_clicky_enabled(void) {
    return clicky_enabled;
}

static void boot_coin_work_handler(struct k_work *work) {
    ARG_UNUSED(work);
    preonic_sound_play_coin();
}

static int preonic_sound_event_listener(const zmk_event_t *eh) {
    const struct zmk_activity_state_changed *act_ev = as_zmk_activity_state_changed(eh);
    if (act_ev != NULL) {
        if (act_ev->state == ZMK_ACTIVITY_SLEEP) {
            // Cancel sounds and power down PWM upon entering deep sleep
            preonic_sound_stop();
        }
        return 0;
    }

    const struct zmk_position_state_changed *pos_ev = as_zmk_position_state_changed(eh);
    if (pos_ev != NULL) {
        if (!pos_ev->state) {
            // Key released - no action
            return 0;
        }

        // Check for Fn + S toggle keypress (Master Sound On/Off)
        if (pos_ev->position == S_KEY_POSITION &&
            (zmk_keymap_layer_active(FN_LAYER_INDEX) || zmk_keymap_layer_active(TRI_LAYER_INDEX))) {
            preonic_sound_toggle_master();
            return 0;
        }

        // Check for Fn + C toggle keypress (Audio Clicky On/Off)
        if (pos_ev->position == C_KEY_POSITION &&
            (zmk_keymap_layer_active(FN_LAYER_INDEX) || zmk_keymap_layer_active(TRI_LAYER_INDEX))) {
            preonic_sound_toggle_clicky();
            return 0;
        }

        // Output crisp clicky tick for general keypress
        preonic_sound_play_click();
        return 0;
    }

    return 0;
}

ZMK_LISTENER(preonic_sound, preonic_sound_event_listener);
ZMK_SUBSCRIPTION(preonic_sound, zmk_position_state_changed);
ZMK_SUBSCRIPTION(preonic_sound, zmk_activity_state_changed);

static int preonic_sound_init(void) {
    k_work_init_delayable(&sound_work, sound_work_handler);
    k_work_init_delayable(&boot_coin_work, boot_coin_work_handler);

    load_sound_state();

    if (!device_is_ready(pwm_dev)) {
        LOG_WRN("Preonic sound PWM device not ready");
        return 0;
    }

    // Ensure PWM starts completely off
    set_tone(0);

#if IS_ENABLED(CONFIG_PREONIC_SOUND_COIN_BOOT)
    // Only play Mario coin on cold boot, NEVER when waking from System OFF sleep
    if (!is_wake_from_system_off() && sound_master_enabled && !cold_boot_done) {
        cold_boot_done = true;
        // Schedule Mario coin chime 600ms after boot
        k_work_schedule(&boot_coin_work, K_MSEC(600));
    }
#endif

    return 0;
}

SYS_INIT(preonic_sound_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
