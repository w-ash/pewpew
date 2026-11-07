/*
 * The capture node's portable C (firmware/audio-node/main: sha256.c,
 * sub.c) on the host, for tests/test_audio_wire.py. One command a line on
 * stdin, one answer a line on stdout; HEX is lowercase hex, `-` for none.
 *
 *   sha HEX                       the SHA-256 of HEX
 *   hmac KEY MSG                  the HMAC-SHA256 of MSG under KEY
 *   init MAC NONCE KEY            a node with that MAC, boot nonce (decimal) and key
 *   sub MSG IP PORT NOW_MS        the node's code for SUB MSG from IP:PORT (IP as 4 bytes of hex)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sha256.h"
#include "sub.h"

static size_t unhex(const char *text, uint8_t *out, size_t room)
{
    if (strcmp(text, "-") == 0) {
        return 0;
    }
    size_t n = strlen(text) / 2;
    for (size_t i = 0; i < n && i < room; i++) {
        unsigned byte;
        sscanf(text + 2 * i, "%2x", &byte);
        out[i] = (uint8_t)byte;
    }
    return n < room ? n : room;
}

static void print_hex(const uint8_t *data, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        printf("%02x", data[i]);
    }
    printf("\n");
}

int main(void)
{
    static char line[8192], a[4096], b[4096], c[256], d[64];
    static uint8_t x[2048], y[2048];
    pp_sub_t sub;
    memset(&sub, 0, sizeof sub);
    while (fgets(line, sizeof line, stdin) != NULL) {
        uint8_t out[PP_SHA256_SIZE];
        if (sscanf(line, "sha %4095s", a) == 1) {
            pp_sha256_t ctx;
            size_t n = unhex(a, x, sizeof x);
            pp_sha256_init(&ctx);
            pp_sha256_update(&ctx, x, n);
            pp_sha256_final(&ctx, out);
            print_hex(out, sizeof out);
        } else if (sscanf(line, "hmac %4095s %4095s", a, b) == 2) {
            size_t kn = unhex(a, x, sizeof x), mn = unhex(b, y, sizeof y);
            pp_hmac_sha256(x, kn, y, mn, out);
            print_hex(out, sizeof out);
        } else if (sscanf(line, "init %4095s %255s %4095s", a, c, b) == 3) {
            memset(&sub, 0, sizeof sub);
            unhex(a, sub.mac, sizeof sub.mac);
            sub.nonce = strtoull(c, NULL, 10);
            sub.has_key = unhex(b, sub.key, sizeof sub.key) == PP_KEY_SIZE;
            printf("ok\n");
        } else if (sscanf(line, "sub %4095s %4095s %255s %63s", a, b, c, d) == 4) {
            uint8_t ip[4];
            size_t n = unhex(a, x, sizeof x);
            unhex(b, ip, sizeof ip);
            printf("%d\n", pp_sub_check(&sub, x, n, ip, (uint16_t)atoi(c), (uint32_t)strtoul(d, NULL, 10)));
        } else {
            printf("?\n");
        }
        fflush(stdout);
    }
    return 0;
}
