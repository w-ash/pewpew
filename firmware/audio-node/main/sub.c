#include "sub.h"

#include <string.h>

#include "sha256.h"

static uint64_t le64(const uint8_t *p)
{
    uint64_t v = 0;
    for (int i = 7; i >= 0; i--) {
        v = v << 8 | p[i];
    }
    return v;
}

/* Compare in time that does not depend on where the bytes differ. */
static bool same(const uint8_t *a, const uint8_t *b, size_t n)
{
    uint8_t diff = 0;
    for (size_t i = 0; i < n; i++) {
        diff |= a[i] ^ b[i];
    }
    return diff == 0;
}

bool pp_sub_streaming(const pp_sub_t *sub, uint32_t now_ms)
{
    return sub->holding && (uint32_t)(now_ms - sub->renewed_ms) < PP_HOLD_MS;
}

int pp_sub_check(pp_sub_t *sub, const uint8_t *msg, size_t len, const uint8_t ip[4], uint16_t port, uint32_t now_ms)
{
    if (len != PP_SUB_SIZE || memcmp(msg, PP_SUB_MAGIC, 2) != 0 || msg[2] != PP_VERSION) {
        return PP_DENY_MALFORMED;
    }
    if (memcmp(msg + 3, sub->mac, 6) != 0) {
        return PP_DENY_OTHER_NODE;
    }
    if (le64(msg + 9) != sub->nonce) {
        return PP_DENY_STALE;
    }
    uint16_t reply_port = (uint16_t)(msg[21] | msg[22] << 8);
    if (memcmp(msg + 17, ip, 4) != 0 || reply_port != port) {
        return PP_DENY_ADDRESS;
    }
    if (!sub->has_key) {
        return PP_DENY_NO_KEY;
    }
    uint8_t tag[PP_TAG_SIZE];
    pp_hmac_sha256(sub->key, PP_KEY_SIZE, msg, PP_SUB_HEAD_SIZE, tag);
    if (!same(tag, msg + PP_SUB_HEAD_SIZE, PP_TAG_SIZE)) {
        return PP_DENY_KEY;
    }
    if (pp_sub_streaming(sub, now_ms) && memcmp(sub->holder_ip, ip, 4) != 0) {
        return PP_DENY_HELD;
    }
    sub->holding = true;
    memcpy(sub->holder_ip, ip, 4);
    sub->holder_port = port;
    sub->renewed_ms = now_ms;
    return 0;
}
