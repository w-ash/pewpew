/*
 * The node's HTTP server, read-only: `GET /json/info` and nothing else.
 * It carries WLED's `ver`, `mac`, `name`, `uptime` and `wifi.rssi`, its
 * `brand` and `product`, so pewpew's scans tell a node from a board, and
 * the node's own fields: `input`, `rate`, `nonce` (the boot nonce a SUB
 * signs, 16 hex digits), `peak` (dBFS over the last second, or null for
 * silence), `key`, `holder`, `reset_reason`, and the stream's counters.
 */
#include <inttypes.h>
#include <math.h>
#include <stdio.h>

#include "esp_app_desc.h"
#include "esp_http_server.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "node.h"

static void ip_text(uint32_t ip, char *out, size_t size)
{
    const uint8_t *b = (const uint8_t *)&ip;
    snprintf(out, size, "\"%u.%u.%u.%u\"", b[0], b[1], b[2], b[3]);
}

static esp_err_t info_get(httpd_req_t *req)
{
    char peak[16] = "null", holder[24] = "null";
    uint32_t level = atomic_load(&g_node.peak);
    if (level > 0) {
        snprintf(peak, sizeof peak, "%.1f", 20.0 * log10(level / 32768.0));
    }
    uint32_t holder_ip = atomic_load(&g_node.holder_ip);
    if (holder_ip != 0) {
        ip_text(holder_ip, holder, sizeof holder);
    }
    wifi_ap_record_t ap;
    int rssi = 0, channel = 0;
    if (esp_wifi_sta_get_ap_info(&ap) == ESP_OK) {
        rssi = ap.rssi;
        channel = ap.primary;
    }
    const uint8_t *m = g_node.mac;
    char body[768];
    int n = snprintf(
        body, sizeof body,
        "{\"ver\":\"%s\",\"name\":\"%s\",\"mdns\":\"%s\",\"mac\":\"%02x%02x%02x%02x%02x%02x\","
        "\"brand\":\"" PP_BRAND "\",\"product\":\"" PP_PRODUCT "\",\"uptime\":%" PRIu64 ","
        "\"wifi\":{\"rssi\":%d,\"channel\":%d},\"input\":\"line\",\"rate\":%d,\"nonce\":\"%016" PRIx64 "\","
        "\"peak\":%s,\"key\":%s,\"holder\":%s,\"reset_reason\":\"%s\","
        "\"sent\":%" PRIu32 ",\"send_errors\":%" PRIu32 ",\"queue_full\":%" PRIu32 ",\"overflows\":%" PRIu32 ","
        "\"overflow_samples\":%" PRIu32 ",\"clips\":%" PRIu32 "}",
        esp_app_get_description()->version, g_node.name, g_node.hostname, m[0], m[1], m[2], m[3], m[4], m[5],
        (uint64_t)(esp_timer_get_time() / 1000000), rssi, channel, PP_RATE, g_node.nonce, peak,
        g_node.has_key ? "true" : "false", holder, g_node.reset_reason, atomic_load(&g_node.sent),
        atomic_load(&g_node.send_errors), atomic_load(&g_node.queue_full), atomic_load(&g_node.overflows),
        atomic_load(&g_node.overflow_samples), atomic_load(&g_node.clips));
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_send(req, body, n);
}

void info_start(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    httpd_handle_t server = NULL;
    ESP_ERROR_CHECK(httpd_start(&server, &config));
    httpd_uri_t info = {.uri = "/json/info", .method = HTTP_GET, .handler = info_get};
    ESP_ERROR_CHECK(httpd_register_uri_handler(server, &info));
}
