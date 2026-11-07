/*
 * Improv serial on the USB port (the native USB Serial/JTAG), so
 * `python -m pewpew wifi PORT --name NAME` sets up a node as it does a
 * WLED board: logs go to the UART port, never here. Written from the
 * Improv serial spec (https://www.improv-wifi.com/serial/, RA-28 S1785):
 *
 *   packet  "IMPROV" version(1) type length data... checksum
 *           (the checksum is the low byte of the sum of every byte before it)
 *   RPC     command length data...
 *
 * Commands: 0x01 Wi-Fi settings, 0x02 current state, 0x03 device info,
 * 0x05 hostname and 0x06 device name (each a get with no data, or a set
 * with the name as the data). The node is always authorized: it has no
 * button to press. A name is 1-32 lowercase letters, digits and hyphens,
 * with no hyphen at either end, the rule `wifi --name` checks.
 */
#include <stdio.h>
#include <string.h>

#include "driver/usb_serial_jtag.h"
#include "esp_app_desc.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "node.h"

#define TYPE_STATE 0x01
#define TYPE_ERROR 0x02
#define TYPE_RPC 0x03
#define TYPE_RESULT 0x04

#define STATE_READY 0x02
#define STATE_PROVISIONING 0x03
#define STATE_PROVISIONED 0x04

#define ERROR_INVALID 0x01
#define ERROR_UNKNOWN_COMMAND 0x02
#define ERROR_CANNOT_CONNECT 0x03
#define ERROR_BAD_HOSTNAME 0x05

#define CMD_WIFI 0x01
#define CMD_STATE 0x02
#define CMD_INFO 0x03
#define CMD_HOSTNAME 0x05
#define CMD_DEVICE_NAME 0x06

#define JOIN_MS 24000 /* a join that has no address by then has failed */
#define POLL_MS 50

static const char *TAG = "improv";
static uint8_t s_state = STATE_READY;
static bool s_joining;
static uint32_t s_join_deadline;

static void send_packet(uint8_t type, const uint8_t *data, uint8_t len)
{
    uint8_t out[6 + 3 + 255 + 1];
    memcpy(out, "IMPROV", 6);
    out[6] = 1;
    out[7] = type;
    out[8] = len;
    memcpy(out + 9, data, len);
    uint8_t sum = 0;
    for (int i = 0; i < 9 + len; i++) {
        sum += out[i];
    }
    out[9 + len] = sum;
    usb_serial_jtag_write_bytes(out, 10 + (size_t)len, pdMS_TO_TICKS(100));
}

static void send_state(void) { send_packet(TYPE_STATE, &s_state, 1); }

static void send_error(uint8_t code) { send_packet(TYPE_ERROR, &code, 1); }

/* An RPC result: the command, the data length, then each string with its length. */
static void send_result(uint8_t command, const char *const *strings, int count)
{
    uint8_t data[255];
    size_t at = 2;
    for (int i = 0; i < count; i++) {
        size_t n = strlen(strings[i]);
        if (n > 64 || at + 1 + n > sizeof data) {
            n = 0;
        }
        data[at++] = (uint8_t)n;
        memcpy(data + at, strings[i], n);
        at += n;
    }
    data[0] = command;
    data[1] = (uint8_t)(at - 2);
    send_packet(TYPE_RESULT, data, (uint8_t)at);
}

static void send_url(uint8_t command)
{
    uint32_t ip = atomic_load(&g_node.ip);
    const uint8_t *b = (const uint8_t *)&ip;
    char url[32];
    snprintf(url, sizeof url, "http://%u.%u.%u.%u", b[0], b[1], b[2], b[3]);
    const char *strings[] = {url};
    send_result(command, strings, 1);
}

static void join(const uint8_t *data, uint8_t len)
{
    uint8_t ssid_len = len > 0 ? data[0] : 0;
    uint8_t pass_len = len > 1 + ssid_len ? data[1 + ssid_len] : 0;
    wifi_config_t cfg = {0};
    if (ssid_len == 0 || ssid_len > sizeof cfg.sta.ssid || pass_len > sizeof cfg.sta.password ||
        2 + ssid_len + pass_len > len) {
        send_error(ERROR_INVALID);
        return;
    }
    memcpy(cfg.sta.ssid, data + 1, ssid_len);
    memcpy(cfg.sta.password, data + 2 + ssid_len, pass_len);
    if (node_join(&cfg) != ESP_OK) {
        send_error(ERROR_CANNOT_CONNECT);
        return;
    }
    s_state = STATE_PROVISIONING;
    s_joining = true;
    s_join_deadline = node_ms() + JOIN_MS;
    send_state();
}

/* Get or set a name: `own` is the node's, set by `apply`. */
static void name_command(uint8_t command, const uint8_t *data, uint8_t len, const char *own, bool hostname)
{
    if (len > 0) {
        if (!node_valid_name((const char *)data, len)) {
            send_error(ERROR_BAD_HOSTNAME);
            return;
        }
        char name[NODE_NAME_MAX + 1];
        memcpy(name, data, len);
        name[len] = '\0';
        node_set_names(hostname ? NULL : name, hostname ? name : NULL);
    }
    const char *strings[] = {own};
    send_result(command, strings, 1);
}

static void handle(const uint8_t *rpc, uint8_t len)
{
    if (len < 2 || rpc[1] != len - 2) {
        send_error(ERROR_INVALID);
        return;
    }
    const uint8_t *data = rpc + 2;
    uint8_t n = rpc[1];
    switch (rpc[0]) {
    case CMD_WIFI:
        join(data, n);
        break;
    case CMD_STATE:
        send_state();
        if (s_state == STATE_PROVISIONED) {
            send_url(CMD_STATE);
        }
        break;
    case CMD_INFO: {
        const char *strings[] = {PP_FIRMWARE, esp_app_get_description()->version, "ESP32-S3", g_node.name};
        send_result(CMD_INFO, strings, 4);
        break;
    }
    case CMD_HOSTNAME:
        name_command(CMD_HOSTNAME, data, n, g_node.hostname, true);
        break;
    case CMD_DEVICE_NAME:
        name_command(CMD_DEVICE_NAME, data, n, g_node.name, false);
        break;
    default:
        send_error(ERROR_UNKNOWN_COMMAND);
    }
}

/* Feed bytes to the packet finder; handle each whole, checked RPC packet. */
static void feed(uint8_t *buf, size_t *used)
{
    for (;;) {
        size_t start = 0;
        while (start + 6 <= *used && memcmp(buf + start, "IMPROV", 6) != 0) {
            start++;
        }
        if (start + 6 > *used) {
            size_t keep = *used < 5 ? *used : 5; /* a header may be split across reads */
            memmove(buf, buf + *used - keep, keep);
            *used = keep;
            return;
        }
        memmove(buf, buf + start, *used - start);
        *used -= start;
        if (*used < 9 || *used < 10 + (size_t)buf[8]) {
            return;
        }
        size_t end = 9 + buf[8];
        uint8_t sum = 0;
        for (size_t i = 0; i < end; i++) {
            sum += buf[i];
        }
        if (buf[6] != 1 || sum != buf[end]) {
            send_error(ERROR_INVALID);
            memmove(buf, buf + 1, *used - 1); /* resync past this header */
            *used -= 1;
            continue;
        }
        if (buf[7] == TYPE_RPC) {
            handle(buf + 9, buf[8]);
        }
        memmove(buf, buf + end + 1, *used - end - 1);
        *used -= end + 1;
    }
}

static void improv_task(void *arg)
{
    static uint8_t buf[512];
    size_t used = 0;
    for (;;) {
        int n = usb_serial_jtag_read_bytes(buf + used, sizeof buf - used, pdMS_TO_TICKS(POLL_MS));
        if (n > 0) {
            used += (size_t)n;
            feed(buf, &used);
            if (used == sizeof buf) {
                used = 0; /* a full buffer with no header in it is noise */
            }
        }
        if (s_joining && atomic_load(&g_node.ip) != 0) {
            s_joining = false;
            s_state = STATE_PROVISIONED;
            send_state();
            send_url(CMD_WIFI);
            ESP_LOGI(TAG, "joined the network");
        } else if (s_joining && (int32_t)(node_ms() - s_join_deadline) > 0) {
            s_joining = false;
            s_state = STATE_READY;
            send_error(ERROR_CANNOT_CONNECT);
            ESP_LOGW(TAG, "could not join the network");
        } else if (!s_joining) {
            s_state = atomic_load(&g_node.ip) != 0 ? STATE_PROVISIONED : STATE_READY;
        }
    }
}

void improv_start(void)
{
    usb_serial_jtag_driver_config_t config = USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(usb_serial_jtag_driver_install(&config));
    xTaskCreatePinnedToCore(improv_task, "improv", 4096, NULL, 5, NULL, 0);
}
