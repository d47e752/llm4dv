// Copyright ***** contributors.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0
//
// SECDED encode code generated by
// util/design/secded_gen.py from util/design/data/secded_cfg.hjson

#include "secded_enc.h"

#include <stdbool.h>
#include <stdint.h>

// Calculates even parity for a 64-bit word
static uint8_t calc_parity(uint64_t word, bool invert) {
  bool parity = false;

  while (word) {
    if (word & 1) {
      parity = !parity;
    }

    word >>= 1;
  }

  return parity ^ invert;
}

uint8_t enc_secded_22_16(const uint8_t bytes[2]) {
  uint16_t word = ((uint16_t)bytes[0] << 0) | ((uint16_t)bytes[1] << 8);

  return (calc_parity(word & 0x496e, false) << 0) |
         (calc_parity(word & 0xf20b, false) << 1) |
         (calc_parity(word & 0x8ed8, false) << 2) |
         (calc_parity(word & 0x7714, false) << 3) |
         (calc_parity(word & 0xaca5, false) << 4) |
         (calc_parity(word & 0x11f3, false) << 5);
}

uint8_t enc_secded_28_22(const uint8_t bytes[3]) {
  uint32_t word = ((uint32_t)bytes[0] << 0) | ((uint32_t)bytes[1] << 8) |
                  ((uint32_t)bytes[2] << 16);

  return (calc_parity(word & 0x3003ff, false) << 0) |
         (calc_parity(word & 0x10fc0f, false) << 1) |
         (calc_parity(word & 0x271c71, false) << 2) |
         (calc_parity(word & 0x3b6592, false) << 3) |
         (calc_parity(word & 0x3daaa4, false) << 4) |
         (calc_parity(word & 0x3ed348, false) << 5);
}

uint8_t enc_secded_39_32(const uint8_t bytes[4]) {
  uint32_t word = ((uint32_t)bytes[0] << 0) | ((uint32_t)bytes[1] << 8) |
                  ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);

  return (calc_parity(word & 0x2606bd25, false) << 0) |
         (calc_parity(word & 0xdeba8050, false) << 1) |
         (calc_parity(word & 0x413d89aa, false) << 2) |
         (calc_parity(word & 0x31234ed1, false) << 3) |
         (calc_parity(word & 0xc2c1323b, false) << 4) |
         (calc_parity(word & 0x2dcc624c, false) << 5) |
         (calc_parity(word & 0x98505586, false) << 6);
}

uint8_t enc_secded_64_57(const uint8_t bytes[8]) {
  uint64_t word = ((uint64_t)bytes[0] << 0) | ((uint64_t)bytes[1] << 8) |
                  ((uint64_t)bytes[2] << 16) | ((uint64_t)bytes[3] << 24) |
                  ((uint64_t)bytes[4] << 32) | ((uint64_t)bytes[5] << 40) |
                  ((uint64_t)bytes[6] << 48) | ((uint64_t)bytes[7] << 56);

  return (calc_parity(word & 0x103fff800007fff, false) << 0) |
         (calc_parity(word & 0x17c1ff801ff801f, false) << 1) |
         (calc_parity(word & 0x1bde1f87e0781e1, false) << 2) |
         (calc_parity(word & 0x1deee3b8e388e22, false) << 3) |
         (calc_parity(word & 0x1ef76cdb2c93244, false) << 4) |
         (calc_parity(word & 0x1f7bb56d5525488, false) << 5) |
         (calc_parity(word & 0x1fbdda769a46910, false) << 6);
}

uint8_t enc_secded_72_64(const uint8_t bytes[8]) {
  uint64_t word = ((uint64_t)bytes[0] << 0) | ((uint64_t)bytes[1] << 8) |
                  ((uint64_t)bytes[2] << 16) | ((uint64_t)bytes[3] << 24) |
                  ((uint64_t)bytes[4] << 32) | ((uint64_t)bytes[5] << 40) |
                  ((uint64_t)bytes[6] << 48) | ((uint64_t)bytes[7] << 56);

  return (calc_parity(word & 0xb9000000001fffff, false) << 0) |
         (calc_parity(word & 0x5e00000fffe0003f, false) << 1) |
         (calc_parity(word & 0x67003ff003e007c1, false) << 2) |
         (calc_parity(word & 0xcd0fc0f03c207842, false) << 3) |
         (calc_parity(word & 0xb671c711c4438884, false) << 4) |
         (calc_parity(word & 0xb5b65926488c9108, false) << 5) |
         (calc_parity(word & 0xcbdaaa4a91152210, false) << 6) |
         (calc_parity(word & 0x7aed348d221a4420, false) << 7);
}

uint8_t enc_secded_inv_22_16(const uint8_t bytes[2]) {
  uint16_t word = ((uint16_t)bytes[0] << 0) | ((uint16_t)bytes[1] << 8);

  return (calc_parity(word & 0x496e, false) << 0) |
         (calc_parity(word & 0xf20b, true) << 1) |
         (calc_parity(word & 0x8ed8, false) << 2) |
         (calc_parity(word & 0x7714, true) << 3) |
         (calc_parity(word & 0xaca5, false) << 4) |
         (calc_parity(word & 0x11f3, true) << 5);
}

uint8_t enc_secded_inv_28_22(const uint8_t bytes[3]) {
  uint32_t word = ((uint32_t)bytes[0] << 0) | ((uint32_t)bytes[1] << 8) |
                  ((uint32_t)bytes[2] << 16);

  return (calc_parity(word & 0x3003ff, false) << 0) |
         (calc_parity(word & 0x10fc0f, true) << 1) |
         (calc_parity(word & 0x271c71, false) << 2) |
         (calc_parity(word & 0x3b6592, true) << 3) |
         (calc_parity(word & 0x3daaa4, false) << 4) |
         (calc_parity(word & 0x3ed348, true) << 5);
}

uint8_t enc_secded_inv_39_32(const uint8_t bytes[4]) {
  uint32_t word = ((uint32_t)bytes[0] << 0) | ((uint32_t)bytes[1] << 8) |
                  ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);

  return (calc_parity(word & 0x2606bd25, false) << 0) |
         (calc_parity(word & 0xdeba8050, true) << 1) |
         (calc_parity(word & 0x413d89aa, false) << 2) |
         (calc_parity(word & 0x31234ed1, true) << 3) |
         (calc_parity(word & 0xc2c1323b, false) << 4) |
         (calc_parity(word & 0x2dcc624c, true) << 5) |
         (calc_parity(word & 0x98505586, false) << 6);
}

uint8_t enc_secded_inv_64_57(const uint8_t bytes[8]) {
  uint64_t word = ((uint64_t)bytes[0] << 0) | ((uint64_t)bytes[1] << 8) |
                  ((uint64_t)bytes[2] << 16) | ((uint64_t)bytes[3] << 24) |
                  ((uint64_t)bytes[4] << 32) | ((uint64_t)bytes[5] << 40) |
                  ((uint64_t)bytes[6] << 48) | ((uint64_t)bytes[7] << 56);

  return (calc_parity(word & 0x103fff800007fff, false) << 0) |
         (calc_parity(word & 0x17c1ff801ff801f, true) << 1) |
         (calc_parity(word & 0x1bde1f87e0781e1, false) << 2) |
         (calc_parity(word & 0x1deee3b8e388e22, true) << 3) |
         (calc_parity(word & 0x1ef76cdb2c93244, false) << 4) |
         (calc_parity(word & 0x1f7bb56d5525488, true) << 5) |
         (calc_parity(word & 0x1fbdda769a46910, false) << 6);
}

uint8_t enc_secded_inv_72_64(const uint8_t bytes[8]) {
  uint64_t word = ((uint64_t)bytes[0] << 0) | ((uint64_t)bytes[1] << 8) |
                  ((uint64_t)bytes[2] << 16) | ((uint64_t)bytes[3] << 24) |
                  ((uint64_t)bytes[4] << 32) | ((uint64_t)bytes[5] << 40) |
                  ((uint64_t)bytes[6] << 48) | ((uint64_t)bytes[7] << 56);

  return (calc_parity(word & 0xb9000000001fffff, false) << 0) |
         (calc_parity(word & 0x5e00000fffe0003f, true) << 1) |
         (calc_parity(word & 0x67003ff003e007c1, false) << 2) |
         (calc_parity(word & 0xcd0fc0f03c207842, true) << 3) |
         (calc_parity(word & 0xb671c711c4438884, false) << 4) |
         (calc_parity(word & 0xb5b65926488c9108, true) << 5) |
         (calc_parity(word & 0xcbdaaa4a91152210, false) << 6) |
         (calc_parity(word & 0x7aed348d221a4420, true) << 7);
}