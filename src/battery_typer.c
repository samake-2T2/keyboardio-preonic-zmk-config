/*
 * Copyright (c) 2026 Keyboardio Preonic Custom Firmware
 * SPDX-License-Identifier: MIT
 */

#include <zephyr/kernel.h>
#include <zephyr/init.h>
#include <zephyr/logging/log.h>
#include <dt-bindings/zmk/keys.h>
#include <dt-bindings/zmk/modifiers.h>
#include <zmk/battery.h>
#include <zmk/events/keycode_state_changed.h>
#include <zmk/activity.h>
#include <zmk/event_manager.h>
#include <zmk/events/activity_state_changed.h>

#include "battery_typer.h"

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

struct key_step {
    uint32_t keycode;
    bool pressed;
};

#define MAX_KEY_STEPS 32
#define TYPING_STEP_INTERVAL_MS 12

static struct key_step steps[MAX_KEY_STEPS];
static size_t num_steps = 0;
static size_t current_step = 0;
static bool typing_in_progress = false;

static struct k_work_delayable typer_work;

static const uint32_t digit_keys[10] = {
    N0, N1, N2, N3, N4, N5, N6, N7, N8, N9
};

static void add_key(uint32_t keycode) {
    if (num_steps + 2 <= MAX_KEY_STEPS) {
        steps[num_steps++] = (struct key_step){ .keycode = keycode, .pressed = true };
        steps[num_steps++] = (struct key_step){ .keycode = keycode, .pressed = false };
    }
}

static void typer_work_handler(struct k_work *work) {
    ARG_UNUSED(work);

    if (!typing_in_progress) {
        return;
    }

    if (current_step < num_steps) {
        struct key_step step = steps[current_step++];
        raise_zmk_keycode_state_changed_from_encoded(step.keycode, step.pressed, k_uptime_get());
        k_work_reschedule(&typer_work, K_MSEC(TYPING_STEP_INTERVAL_MS));
    } else {
        typing_in_progress = false;
        num_steps = 0;
        current_step = 0;
    }
}

void preonic_type_battery_status(void) {
    if (typing_in_progress) {
        return;
    }

    uint8_t soc = zmk_battery_state_of_charge();
    if (soc > 100) {
        soc = 100;
    }

    num_steps = 0;
    current_step = 0;

    // Type "Battery: "
    add_key(LS(B));
    add_key(A);
    add_key(T);
    add_key(T);
    add_key(E);
    add_key(R);
    add_key(Y);
    add_key(COLON);
    add_key(SPACE);

    // Type percentage value
    if (soc == 100) {
        add_key(N1);
        add_key(N0);
        add_key(N0);
    } else if (soc >= 10) {
        add_key(digit_keys[soc / 10]);
        add_key(digit_keys[soc % 10]);
    } else {
        add_key(digit_keys[soc]);
    }

    // Type "%"
    add_key(PERCENT);

    typing_in_progress = true;
    k_work_reschedule(&typer_work, K_NO_WAIT);
}

static int battery_typer_event_listener(const zmk_event_t *eh) {
    const struct zmk_activity_state_changed *act_ev = as_zmk_activity_state_changed(eh);
    if (act_ev != NULL) {
        if (act_ev->state == ZMK_ACTIVITY_SLEEP) {
            if (typing_in_progress) {
                k_work_cancel_delayable(&typer_work);
                if (current_step > 0 && steps[current_step - 1].pressed) {
                    raise_zmk_keycode_state_changed_from_encoded(steps[current_step - 1].keycode, false, k_uptime_get());
                }
                typing_in_progress = false;
                num_steps = 0;
                current_step = 0;
            }
        }
    }
    return 0;
}

ZMK_LISTENER(battery_typer, battery_typer_event_listener);
ZMK_SUBSCRIPTION(battery_typer, zmk_activity_state_changed);

static int battery_typer_init(void) {
    k_work_init_delayable(&typer_work, typer_work_handler);
    return 0;
}

SYS_INIT(battery_typer_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
