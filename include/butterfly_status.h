/*
 * Copyright (c) 2026 Keyboardio Preonic Custom Firmware
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <zephyr/kernel.h>

enum butterfly_macro_mode {
    BUTTERFLY_MACRO_IDLE = 0,
    BUTTERFLY_MACRO_REC_1,
    BUTTERFLY_MACRO_REC_2,
    BUTTERFLY_MACRO_REC_3,
    BUTTERFLY_MACRO_PLAY_1,
    BUTTERFLY_MACRO_PLAY_2,
    BUTTERFLY_MACRO_PLAY_3,
};

void butterfly_status_refresh(void);
void butterfly_show_battery(void);
void butterfly_set_macro_mode(enum butterfly_macro_mode mode);
void butterfly_show_password_length(uint8_t length);
void butterfly_show_password_success(void);
void butterfly_show_studio_unlock(void);
