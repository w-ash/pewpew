/*
 * SHA-256 (FIPS 180-4) and HMAC-SHA256 (RFC 2104), in portable C with no
 * IDF header, so tests/test_audio_wire.py compiles and checks them on the
 * host against Python's hashlib and hmac.
 */
#pragma once

#include <stddef.h>
#include <stdint.h>

#define PP_SHA256_SIZE 32

typedef struct {
    uint32_t h[8];
    uint8_t block[64];
    size_t used;    /* bytes in `block` */
    uint64_t total; /* bytes hashed so far */
} pp_sha256_t;

void pp_sha256_init(pp_sha256_t *ctx);
void pp_sha256_update(pp_sha256_t *ctx, const uint8_t *data, size_t len);
void pp_sha256_final(pp_sha256_t *ctx, uint8_t out[PP_SHA256_SIZE]);

void pp_hmac_sha256(const uint8_t *key, size_t key_len, const uint8_t *msg, size_t len,
                    uint8_t out[PP_SHA256_SIZE]);
