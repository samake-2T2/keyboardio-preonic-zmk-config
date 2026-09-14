/*
 * Copyright (c) 2026 Keyboardio Preonic Custom Firmware
 * SPDX-License-Identifier: MIT
 */

#include <zephyr/kernel.h>
#include <zephyr/init.h>
#include <zephyr/logging/log.h>
#include <zephyr/settings/settings.h>
#include <dt-bindings/zmk/keys.h>
#include <dt-bindings/zmk/modifiers.h>
#include <zmk/activity.h>
#include <zmk/event_manager.h>
#include <zmk/events/activity_state_changed.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/events/keycode_state_changed.h>
#include <zmk/keymap.h>

#include "butterfly_status.h"
#include "preonic_sound.h"
#include "dynamic_macro.h"

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#define DYN_MACRO_MAX_STEPS 128
#define DYN_MACRO_STEP_INTERVAL_MS 12

#define FN_LAYER_INDEX 3
#define TRI_LAYER_INDEX 4

// Matrix positions on Row 1 (Number row)
#define MACRO_1_REC_POSITION 8   // Fn + 5 (RC(1,5))
#define MACRO_1_PLAY_POSITION 9  // Fn + 6 (RC(1,6))
#define MACRO_2_REC_POSITION 10  // Fn + 7 (RC(1,7))
#define MACRO_2_PLAY_POSITION 11 // Fn + 8 (RC(1,8))
#define MACRO_3_REC_POSITION 12  // Fn + 9 (RC(1,9))
#define MACRO_3_PLAY_POSITION 13 // Fn + 0 (RC(1,10))

struct __packed dyn_macro_step {
    uint32_t keycode;
    uint8_t pressed;
};

struct __packed dyn_macro_slot {
    uint16_t count;
    struct dyn_macro_step steps[DYN_MACRO_MAX_STEPS];
};

static struct dyn_macro_slot slot1;
static struct dyn_macro_slot slot2;
static struct dyn_macro_slot slot3;

static inline struct dyn_macro_slot *get_slot_ptr(uint8_t slot_num) {
    if (slot_num == 1) return &slot1;
    if (slot_num == 2) return &slot2;
    if (slot_num == 3) return &slot3;
    return NULL;
}

static uint8_t recording_slot = 0; // 0: idle, 1: slot 1, 2: slot 2, 3: slot 3
static uint8_t playing_slot = 0;   // 0: idle, 1: slot 1, 2: slot 2, 3: slot 3
static uint16_t play_step_idx = 0;

static struct k_work_delayable play_work;

#if IS_ENABLED(CONFIG_SETTINGS)
static int macro_settings_set(const char *name, size_t len, settings_read_cb read_cb, void *cb_arg) {
    const char *next;
    if (settings_name_steq(name, "1", &next) && !next) {
        if (len <= sizeof(slot1)) {
            read_cb(cb_arg, &slot1, len);
            if (slot1.count > DYN_MACRO_MAX_STEPS) {
                slot1.count = 0;
            }
            LOG_INF("Loaded Dynamic Macro 1 from Flash (%u steps)", slot1.count);
        }
        return 0;
    }
    if (settings_name_steq(name, "2", &next) && !next) {
        if (len <= sizeof(slot2)) {
            read_cb(cb_arg, &slot2, len);
            if (slot2.count > DYN_MACRO_MAX_STEPS) {
                slot2.count = 0;
            }
            LOG_INF("Loaded Dynamic Macro 2 from Flash (%u steps)", slot2.count);
        }
        return 0;
    }
    if (settings_name_steq(name, "3", &next) && !next) {
        if (len <= sizeof(slot3)) {
            read_cb(cb_arg, &slot3, len);
            if (slot3.count > DYN_MACRO_MAX_STEPS) {
                slot3.count = 0;
            }
            LOG_INF("Loaded Dynamic Macro 3 from Flash (%u steps)", slot3.count);
        }
        return 0;
    }
    return -ENOENT;
}

struct settings_handler macro_settings_conf = {
    .name = "dyn_macro",
    .h_set = macro_settings_set,
};

static void dynamic_macro_save_slot(uint8_t slot_num) {
    if (slot_num == 1) {
        settings_save_one("dyn_macro/1", &slot1, sizeof(slot1));
        LOG_INF("Saved Dynamic Macro 1 to Flash (%u steps)", slot1.count);
    } else if (slot_num == 2) {
        settings_save_one("dyn_macro/2", &slot2, sizeof(slot2));
        LOG_INF("Saved Dynamic Macro 2 to Flash (%u steps)", slot2.count);
    } else if (slot_num == 3) {
        settings_save_one("dyn_macro/3", &slot3, sizeof(slot3));
        LOG_INF("Saved Dynamic Macro 3 to Flash (%u steps)", slot3.count);
    }
}
#else
static inline void dynamic_macro_save_slot(uint8_t slot_num) { ARG_UNUSED(slot_num); }
#endif

uint8_t dynamic_macro_get_recording_slot(void) {
    return recording_slot;
}

uint8_t dynamic_macro_get_playing_slot(void) {
    return playing_slot;
}

void dynamic_macro_record_toggle(uint8_t slot_num) {
    if (slot_num < 1 || slot_num > 3) {
        return;
    }
    if (playing_slot != 0) {
        return; // Disallow record toggle during active playback
    }

    struct dyn_macro_slot *slot = get_slot_ptr(slot_num);
    if (!slot) {
        return;
    }

    if (recording_slot == slot_num) {
        // Stop recording current slot
        // Defensive: append release steps for any key left in pressed state
        for (uint16_t i = 0; i < slot->count; i++) {
            if (slot->steps[i].pressed) {
                bool released = false;
                for (uint16_t j = i + 1; j < slot->count; j++) {
                    if (slot->steps[j].keycode == slot->steps[i].keycode && !slot->steps[j].pressed) {
                        released = true;
                        break;
                    }
                }
                if (!released && slot->count < DYN_MACRO_MAX_STEPS) {
                    slot->steps[slot->count++] = (struct dyn_macro_step){
                        .keycode = slot->steps[i].keycode,
                        .pressed = 0
                    };
                }
            }
        }

        recording_slot = 0;
        butterfly_set_macro_mode(BUTTERFLY_MACRO_IDLE);
        preonic_sound_play_macro_rec_stop();
        dynamic_macro_save_slot(slot_num);
        LOG_INF("Dynamic Macro %u recorded: %u steps", slot_num, slot->count);
    } else {
        // If another slot was recording, cancel it first
        if (recording_slot != 0) {
            butterfly_set_macro_mode(BUTTERFLY_MACRO_IDLE);
        }

        // Start recording new slot: CLEAR PREVIOUS DATA (Overwrite)
        slot->count = 0;
        recording_slot = slot_num;

        enum butterfly_macro_mode m = (slot_num == 1) ? BUTTERFLY_MACRO_REC_1 :
                                      ((slot_num == 2) ? BUTTERFLY_MACRO_REC_2 : BUTTERFLY_MACRO_REC_3);
        butterfly_set_macro_mode(m);
        preonic_sound_play_macro_rec_start();
        LOG_INF("Dynamic Macro %u recording started (buffer cleared)", slot_num);
    }
}

void dynamic_macro_play(uint8_t slot_num) {
    if (slot_num < 1 || slot_num > 3) {
        return;
    }

    // If recording is active, stop it first
    if (recording_slot != 0) {
        dynamic_macro_record_toggle(recording_slot);
        return;
    }

    if (playing_slot != 0) {
        return; // Already playing
    }

    struct dyn_macro_slot *slot = get_slot_ptr(slot_num);
    if (!slot || slot->count == 0) {
        LOG_WRN("Dynamic Macro %u is empty, nothing to play", slot_num);
        return;
    }

    playing_slot = slot_num;
    play_step_idx = 0;

    enum butterfly_macro_mode m = (slot_num == 1) ? BUTTERFLY_MACRO_PLAY_1 :
                                  ((slot_num == 2) ? BUTTERFLY_MACRO_PLAY_2 : BUTTERFLY_MACRO_PLAY_3);
    butterfly_set_macro_mode(m);
    preonic_sound_play_macro_play();

    LOG_INF("Dynamic Macro %u playback started (%u steps)", slot_num, slot->count);
    k_work_reschedule(&play_work, K_NO_WAIT);
}

static void play_work_handler(struct k_work *work) {
    ARG_UNUSED(work);

    if (playing_slot == 0) {
        return;
    }

    struct dyn_macro_slot *slot = get_slot_ptr(playing_slot);
    if (!slot) {
        playing_slot = 0;
        return;
    }
    if (play_step_idx < slot->count) {
        struct dyn_macro_step step = slot->steps[play_step_idx++];
        raise_zmk_keycode_state_changed_from_encoded(step.keycode, (step.pressed != 0), k_uptime_get());
        k_work_reschedule(&play_work, K_MSEC(DYN_MACRO_STEP_INTERVAL_MS));
    } else {
        LOG_INF("Dynamic Macro %u playback finished", playing_slot);
        playing_slot = 0;
        play_step_idx = 0;
    }
}

static int dynamic_macro_event_listener(const zmk_event_t *eh) {
    const struct zmk_activity_state_changed *act_ev = as_zmk_activity_state_changed(eh);
    if (act_ev != NULL) {
        if (act_ev->state == ZMK_ACTIVITY_SLEEP) {
            if (playing_slot != 0) {
                k_work_cancel_delayable(&play_work);
                playing_slot = 0;
                play_step_idx = 0;
            }
            if (recording_slot != 0) {
                recording_slot = 0;
                butterfly_set_macro_mode(BUTTERFLY_MACRO_IDLE);
            }
        }
        return 0;
    }

    const struct zmk_position_state_changed *pos_ev = as_zmk_position_state_changed(eh);
    if (pos_ev != NULL && pos_ev->state) {
        if (zmk_keymap_layer_active(FN_LAYER_INDEX) || zmk_keymap_layer_active(TRI_LAYER_INDEX)) {
            if (pos_ev->position == MACRO_1_REC_POSITION) {
                dynamic_macro_record_toggle(1);
                return ZMK_EV_EVENT_HANDLED;
            } else if (pos_ev->position == MACRO_1_PLAY_POSITION) {
                dynamic_macro_play(1);
                return ZMK_EV_EVENT_HANDLED;
            } else if (pos_ev->position == MACRO_2_REC_POSITION) {
                dynamic_macro_record_toggle(2);
                return ZMK_EV_EVENT_HANDLED;
            } else if (pos_ev->position == MACRO_2_PLAY_POSITION) {
                dynamic_macro_play(2);
                return ZMK_EV_EVENT_HANDLED;
            } else if (pos_ev->position == MACRO_3_REC_POSITION) {
                dynamic_macro_record_toggle(3);
                return ZMK_EV_EVENT_HANDLED;
            } else if (pos_ev->position == MACRO_3_PLAY_POSITION) {
                dynamic_macro_play(3);
                return ZMK_EV_EVENT_HANDLED;
            }
        }
    }

    const struct zmk_keycode_state_changed *kc_ev = as_zmk_keycode_state_changed(eh);
    if (kc_ev != NULL && recording_slot != 0 && playing_slot == 0) {
        struct dyn_macro_slot *slot = get_slot_ptr(recording_slot);
        if (slot && slot->count < DYN_MACRO_MAX_STEPS) {
            slot->steps[slot->count++] = (struct dyn_macro_step){
                .keycode = kc_ev->keycode,
                .pressed = kc_ev->state ? 1 : 0
            };
            if (slot->count >= DYN_MACRO_MAX_STEPS) {
                LOG_WRN("Dynamic Macro %u reached max capacity (%u steps), auto-saving", recording_slot, DYN_MACRO_MAX_STEPS);
                preonic_sound_play_macro_full();
                dynamic_macro_record_toggle(recording_slot);
            }
        }
    }

    return 0;
}

ZMK_LISTENER(dynamic_macro, dynamic_macro_event_listener);
ZMK_SUBSCRIPTION(dynamic_macro, zmk_position_state_changed);
ZMK_SUBSCRIPTION(dynamic_macro, zmk_keycode_state_changed);
ZMK_SUBSCRIPTION(dynamic_macro, zmk_activity_state_changed);

static int dynamic_macro_init(void) {
    k_work_init_delayable(&play_work, play_work_handler);
#if IS_ENABLED(CONFIG_SETTINGS)
    settings_register(&macro_settings_conf);
#endif
    return 0;
}

SYS_INIT(dynamic_macro_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
