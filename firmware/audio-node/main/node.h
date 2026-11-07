/*
 * What the node's tasks share. Each field has one writer, named beside it;
 * the counters are atomics, so /json/info reads them from its own task.
 */
#pragma once

#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>

#include "esp_netif.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "wire.h"

#define NODE_NAME_MAX 32

/* One packet, from the capture task to the stream task. */
typedef struct {
    uint16_t samples;
    uint8_t data[PP_HEADER_SIZE + 2 * PP_SAMPLES];
} node_packet_t;

typedef struct {
    /* Set at boot, before the tasks start. */
    uint8_t mac[6];
    uint64_t nonce;
    bool has_key;
    const char *reset_reason;
    esp_netif_t *netif;
    QueueHandle_t packets;
    /* The Improv task's, once the tasks run. */
    char name[NODE_NAME_MAX + 1];
    char hostname[NODE_NAME_MAX + 1];
    /* The Wi-Fi event handler's and node_join's: this node's IPv4 address, network order, or 0. */
    _Atomic uint32_t ip;
    /* The stream task's. */
    _Atomic bool streaming;
    _Atomic uint32_t holder_ip; /* network order, or 0 */
    _Atomic uint32_t last_send_ms;
    _Atomic uint32_t sent;
    _Atomic uint32_t send_errors;
    /* The capture task's. */
    _Atomic uint32_t queue_full; /* packets dropped because the stream task fell behind */
    _Atomic uint32_t overflows;  /* times the I2S driver dropped samples */
    _Atomic uint32_t overflow_samples;
    _Atomic uint32_t clips;
    _Atomic uint32_t peak; /* the largest |sample| of the last whole second, 0 to 32768 */
} node_t;

extern node_t g_node;

uint32_t node_ms(void);
bool node_valid_name(const char *name, size_t len);
void node_set_names(const char *name, const char *hostname);
esp_err_t node_join(wifi_config_t *cfg);

void capture_start(void);
void stream_start(const uint8_t *key);
void info_start(void);
void improv_start(void);
void led_init(void);
void led_set(uint8_t r, uint8_t g, uint8_t b);
