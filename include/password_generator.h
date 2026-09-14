/*
 * Copyright (c) 2026 Keyboardio Preonic Custom Firmware
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

enum password_mode {
    PW_MODE_DB_SAFE = 0,    /**< DB & Config Safe (A-Z, a-z, 0-9, _, -) */
    PW_MODE_WEB_EXTENDED,   /**< Web Extended with specials (A-Z, a-z, 0-9, _, -, @, .) */
    PW_MODE_ALPHANUMERIC,   /**< Alphanumeric only (A-Z, a-z, 0-9) */
};

/**
 * @brief Cycle through allowed password lengths (12, 16, 20, 24).
 *
 * @param direction +1 for clockwise (longer), -1 for counter-clockwise (shorter)
 */
void password_generator_cycle_length(int direction);

/**
 * @brief Get currently selected password length.
 */
uint8_t password_generator_get_length(void);

/**
 * @brief Trigger generation and typing of a random password.
 *
 * @param mode Generation mode (DB Safe, Web Extended, or Alphanumeric)
 */
void password_generator_trigger(enum password_mode mode);

/**
 * @brief Check if password typing is currently in progress.
 */
bool password_generator_is_typing(void);

#ifdef __cplusplus
}
#endif
