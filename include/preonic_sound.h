/*
 * Copyright (c) 2026 Keyboardio Preonic Custom Firmware
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize piezo sound subsystem.
 */
int preonic_sound_init(void);

/**
 * @brief Play a single tone with specified frequency and duration.
 *
 * @param freq_hz Frequency in Hertz (0 to stop)
 * @param duration_ms Duration in milliseconds
 */
void preonic_sound_play_tone(uint32_t freq_hz, uint32_t duration_ms);

/**
 * @brief Stop any ongoing sound immediately and shut down PWM.
 */
void preonic_sound_stop(void);

/**
 * @brief Play Super Mario coin sound greeting (B5 988Hz -> E6 1319Hz).
 */
void preonic_sound_play_coin(void);

/**
 * @brief Play short audio clicky pulse.
 */
void preonic_sound_play_click(void);

/**
 * @brief Toggle audio clicky state (enabled/disabled).
 *
 * Emits a high confirmation beep (2400Hz) when enabled,
 * or a low confirmation beep (1200Hz) when disabled.
 *
 * @return Current clicky state after toggle (true: enabled, false: disabled)
 */
bool preonic_sound_toggle_clicky(void);

/**
 * @brief Check if audio clicky is currently enabled.
 */
bool preonic_sound_is_clicky_enabled(void);

#ifdef __cplusplus
}
#endif
