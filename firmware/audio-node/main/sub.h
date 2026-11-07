/*
 * The node's half of a subscription (wire.h): it checks a SUB against
 * itself and its source, and keeps one holder. Portable C with no IDF
 * header, so tests/test_audio_wire.py compiles it on the host and checks
 * it against pewpew.audio.wire.
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "wire.h"

typedef struct {
    /* The node's own, set once at boot. */
    uint8_t mac[6];
    uint64_t nonce;
    uint8_t key[PP_KEY_SIZE];
    bool has_key;
    /* The holder: the host the stream goes to while it renews. */
    bool holding;
    uint8_t holder_ip[4]; /* network order */
    uint16_t holder_port;
    uint32_t renewed_ms;
} pp_sub_t;

/*
 * Check `msg`, `len` bytes from `ip` (network order) and `port`, at
 * `now_ms`. Returns 0 and makes the source the holder when the SUB is
 * good, else the PP_DENY_* code of the first check it fails: the length,
 * magic and version; the MAC; the boot nonce; the reply address against
 * the source; the key; and the holder, who keeps the stream while it
 * renews (a new port from the holder's address moves it).
 */
int pp_sub_check(pp_sub_t *sub, const uint8_t *msg, size_t len, const uint8_t ip[4], uint16_t port, uint32_t now_ms);

/* Whether a holder renewed within PP_HOLD_MS of `now_ms`. */
bool pp_sub_streaming(const pp_sub_t *sub, uint32_t now_ms);
