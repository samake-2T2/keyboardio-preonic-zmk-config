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

/**
 * @brief Toggle dynamic macro recording for the specified slot.
 *
 * If the specified slot is already recording, stops recording, plays confirmation chime,
 * and saves the macro to persistent Flash (NVS).
 * If another slot or no slot was recording, clears the slot and starts recording fresh keys.
 *
 * @param slot_num Macro slot number (1 or 2)
 */
void dynamic_macro_record_toggle(uint8_t slot_num);

/**
 * @brief Replay recorded keystrokes from the specified macro slot.
 *
 * Keys are typed asynchronously using a 12ms fixed safe delay (press 12ms, release 12ms)
 * to ensure 100% reliable BLE HID packet delivery without dropped characters.
 *
 * @param slot_num Macro slot number (1 or 2)
 */
void dynamic_macro_play(uint8_t slot_num);

/**
 * @brief Check if dynamic macro recording is currently active.
 *
 * @return Slot number currently recording (1 or 2), or 0 if idle.
 */
uint8_t dynamic_macro_get_recording_slot(void);

/**
 * @brief Check if dynamic macro playback is currently active.
 *
 * @return Slot number currently playing (1 or 2), or 0 if idle.
 */
uint8_t dynamic_macro_get_playing_slot(void);

#ifdef __cplusplus
}
#endif
