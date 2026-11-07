/*
 * The capture node's wire format (ADR-009, 2026-11-06 amendment "capture
 * nodes"). pewpew.audio.wire holds the same values, and
 * tests/test_audio_wire.py checks that the two agree.
 *
 * Every number is little-endian.
 *
 *   audio   "PA" version flags index:u64 nonce:u64, then 1..PP_MAX_SAMPLES
 *           s16 samples (PP_SAMPLES, one 10 ms hop, unless the I2S driver
 *           dropped samples inside the packet). `index` is the first
 *           sample's, counted from boot, dropped samples included.
 *   sub     "PS" version mac:6 nonce:u64 ip:4 port:u16, then an
 *           HMAC-SHA256 tag over those 23 bytes under the node's key.
 *           `ip` (network order) and `port` are where the host wants the
 *           stream: the address it sends the SUB from.
 *   refusal "PR" version code: why the node refused a SUB.
 */
#pragma once

#define PP_PORT 7448
#define PP_RATE 48000
#define PP_SAMPLES 480
#define PP_MAX_SAMPLES 726
#define PP_VERSION 1

#define PP_AUDIO_MAGIC "PA"
#define PP_SUB_MAGIC "PS"
#define PP_REFUSAL_MAGIC "PR"

#define PP_HEADER_SIZE 20
#define PP_SUB_HEAD_SIZE 23
#define PP_TAG_SIZE 32
#define PP_SUB_SIZE 55
#define PP_REFUSAL_SIZE 4
#define PP_KEY_SIZE 32

#define PP_FLAG_CLIP 0x01
#define PP_FLAG_OVERFLOW 0x02

/* A holder keeps the stream this long after its last SUB. */
#define PP_HOLD_MS 3000

#define PP_DENY_MALFORMED 1
#define PP_DENY_OTHER_NODE 2
#define PP_DENY_STALE 3
#define PP_DENY_ADDRESS 4
#define PP_DENY_NO_KEY 5
#define PP_DENY_KEY 6
#define PP_DENY_HELD 7

#define PP_BRAND "pewpew"
#define PP_PRODUCT "audio-node"
#define PP_FIRMWARE "pewpew-audio-node"
