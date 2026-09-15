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

/**
 * @brief Get current dynamic password generator configuration.
 *
 * @param default_len Pointer to store default password length (optional, can be NULL)
 * @param interval_ms Pointer to store typing step interval in ms (optional, can be NULL)
 * @param specials Pointer to buffer for custom special characters (optional, can be NULL)
 * @param specials_len Pointer to store length of custom special characters (optional, can be NULL)
 */
void password_generator_get_config(uint8_t *default_len, uint8_t *interval_ms, char *specials, uint8_t *specials_len);

/**
 * @brief Update dynamic password generator configuration and save to NVS flash.
 *
 * @param default_len Default password length (e.g. 12, 16, 20, 24)
 * @param interval_ms Typing delay interval per step in ms (5..50 ms)
 * @param specials Custom special characters pool string
 * @param specials_len Number of characters in specials (max 32)
 * @return 0 on success, negative error code on invalid parameter
 */
int password_generator_set_config(uint8_t default_len, uint8_t interval_ms, const char *specials, uint8_t specials_len);

#ifdef __cplusplus
}
#endif

