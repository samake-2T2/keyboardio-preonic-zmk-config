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
 * @brief Play low battery double-beep warning sequence (1500Hz).
 */
void preonic_sound_play_low_battery_warning(void);

/**
 * @brief Play short audio clicky pulse.
 */
void preonic_sound_play_click(void);

/**
 * @brief Toggle master sound state (enabled/disabled).
 *
 * When master sound is disabled, all audio (clicky, chimes, beeps) is muted.
 * When enabled, plays a rising confirmation tone.
 *
 * @return Current master sound state after toggle (true: enabled, false: disabled)
 */
bool preonic_sound_toggle_master(void);

/**
 * @brief Check if master sound is currently enabled.
 */
bool preonic_sound_is_master_enabled(void);

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

/**
 * @brief Play dynamic macro recording start chime (rising 2-tone A6 -> D7).
 */
void preonic_sound_play_macro_rec_start(void);

/**
 * @brief Play dynamic macro recording stop chime (double confirmation beep).
 */
void preonic_sound_play_macro_rec_stop(void);

/**
 * @brief Play dynamic macro playback confirmation click/chirp.
 */
void preonic_sound_play_macro_play(void);

/**
 * @brief Play dynamic macro buffer full warning buzz.
 */
void preonic_sound_play_macro_full(void);

#ifdef __cplusplus
}
#endif
