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

#define PREONIC_STUDIO_SOF 0xAB
#define PREONIC_STUDIO_EOF 0xAD
#define PREONIC_STUDIO_MAX_PAYLOAD 64

#define CMD_PING            0x01
#define CMD_HANDSHAKE       0x02
#define CMD_GET_LOCK_STATUS 0x03
#define CMD_LOCK            0x04
#define CMD_GET_STATUS      0x05

#define CMD_GET_KEY         0x10
#define CMD_SET_KEY         0x11
#define CMD_SAVE_KEYMAP     0x12
#define CMD_DISCARD_KEYMAP  0x13

#define CMD_GET_KNOB        0x20
#define CMD_SET_KNOB        0x21

#define CMD_GET_MACRO       0x30
#define CMD_SET_MACRO       0x31
#define CMD_PLAY_MACRO      0x32

#define CMD_GET_PW_CONFIG   0x40
#define CMD_SET_PW_CONFIG   0x41

#define CMD_GET_MOUSE_CFG   0x50
#define CMD_SET_MOUSE_CFG   0x51

#define CMD_GET_AUDIO_CFG   0x60
#define CMD_SET_AUDIO_CFG   0x61
#define CMD_TEST_PIEZO      0x62

#define EVT_UNLOCKED        0xFE
#define EVT_LOCKED          0xFD

#define STATUS_OK           0x00
#define STATUS_ERR_INVALID  0x01
#define STATUS_ERR_LOCKED   0xEE

void preonic_studio_init(void);
bool preonic_studio_is_locked(void);
void preonic_studio_unlock(void);
void preonic_studio_lock(void);
void preonic_studio_process_byte(uint8_t byte);

#ifdef __cplusplus
}
#endif
