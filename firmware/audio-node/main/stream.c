/*
 * The stream: one UDP socket on PP_PORT that takes SUBs and sends the
 * packets to the holder (wire.h, sub.h). One task does both, so the
 * socket has one user. A refused SUB gets a refusal with its code; the
 * stream goes to the holder from the SUB it accepts until PP_HOLD_MS pass
 * without one.
 */
#include <string.h>

#include "esp_log.h"
#include "esp_task_wdt.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lwip/sockets.h"
#include "node.h"
#include "sub.h"

#define WAIT_MS 10 /* the longest the task waits for a packet before it reads the socket again */

static const char *TAG = "stream";
static int s_sock = -1;
static pp_sub_t s_sub;

/* Answer every SUB waiting on the socket. */
static void take_subs(void)
{
    uint8_t msg[64];
    for (;;) {
        struct sockaddr_in from;
        socklen_t from_len = sizeof from;
        int n = recvfrom(s_sock, msg, sizeof msg, MSG_DONTWAIT, (struct sockaddr *)&from, &from_len);
        if (n < 0) {
            return;
        }
        bool was = pp_sub_streaming(&s_sub, node_ms());
        int code = pp_sub_check(&s_sub, msg, (size_t)n, (const uint8_t *)&from.sin_addr.s_addr, ntohs(from.sin_port),
                                node_ms());
        if (code != 0) {
            uint8_t refusal[PP_REFUSAL_SIZE] = {PP_REFUSAL_MAGIC[0], PP_REFUSAL_MAGIC[1], PP_VERSION, (uint8_t)code};
            sendto(s_sock, refusal, sizeof refusal, MSG_DONTWAIT, (struct sockaddr *)&from, from_len);
        } else if (!was) {
            atomic_store(&g_node.last_send_ms, node_ms()); /* the stall clock starts at the subscribe */
            const uint8_t *ip = (const uint8_t *)&from.sin_addr.s_addr;
            ESP_LOGI(TAG, "streaming to %u.%u.%u.%u:%u", ip[0], ip[1], ip[2], ip[3], ntohs(from.sin_port));
        }
    }
}

static void stream_task(void *arg)
{
    static node_packet_t pkt;
    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
    for (;;) {
        esp_task_wdt_reset();
        take_subs();
        bool on = pp_sub_streaming(&s_sub, node_ms());
        uint32_t holder;
        memcpy(&holder, s_sub.holder_ip, 4);
        atomic_store(&g_node.holder_ip, on ? holder : 0);
        atomic_store(&g_node.streaming, on);
        if (xQueueReceive(g_node.packets, &pkt, pdMS_TO_TICKS(WAIT_MS)) != pdTRUE || !on) {
            continue;
        }
        struct sockaddr_in to = {
            .sin_family = AF_INET,
            .sin_port = htons(s_sub.holder_port),
            .sin_addr.s_addr = holder,
        };
        int sent = sendto(s_sock, pkt.data, PP_HEADER_SIZE + 2 * (size_t)pkt.samples, MSG_DONTWAIT,
                          (struct sockaddr *)&to, sizeof to);
        if (sent < 0) {
            atomic_fetch_add(&g_node.send_errors, 1);
        } else {
            atomic_fetch_add(&g_node.sent, 1);
            atomic_store(&g_node.last_send_ms, node_ms());
        }
    }
}

void stream_start(const uint8_t *key)
{
    memcpy(s_sub.mac, g_node.mac, sizeof s_sub.mac);
    s_sub.nonce = g_node.nonce;
    s_sub.has_key = key != NULL;
    if (key != NULL) {
        memcpy(s_sub.key, key, PP_KEY_SIZE);
    }
    s_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    struct sockaddr_in at = {
        .sin_family = AF_INET,
        .sin_port = htons(PP_PORT),
        .sin_addr.s_addr = htonl(INADDR_ANY),
    };
    if (s_sock < 0 || bind(s_sock, (struct sockaddr *)&at, sizeof at) != 0) {
        ESP_LOGE(TAG, "cannot open UDP port %d", PP_PORT);
        abort();
    }
    xTaskCreatePinnedToCore(stream_task, "stream", 4096, NULL, 15, NULL, 0);
}
