/*
 * The devkit's RGB LED, a WS2812 on GPIO38 (ESP32-S3-DevKitC-1 v1.1),
 * driven by the RMT peripheral's bytes encoder at 10 MHz: a 0 bit is
 * 0.3 us high then 0.9 us low, a 1 bit the reverse, in GRB order.
 */
#include "driver/rmt_tx.h"
#include "node.h"

#define LED_GPIO 38
#define TICKS_PER_US 10

static rmt_channel_handle_t s_chan;
static rmt_encoder_handle_t s_encoder;

void led_init(void)
{
    rmt_tx_channel_config_t chan = {
        .gpio_num = LED_GPIO,
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = TICKS_PER_US * 1000000,
        .mem_block_symbols = 48,
        .trans_queue_depth = 2,
    };
    ESP_ERROR_CHECK(rmt_new_tx_channel(&chan, &s_chan));
    rmt_bytes_encoder_config_t bytes = {
        .bit0 = {.level0 = 1, .duration0 = 3, .level1 = 0, .duration1 = 9},
        .bit1 = {.level0 = 1, .duration0 = 9, .level1 = 0, .duration1 = 3},
        .flags.msb_first = 1,
    };
    ESP_ERROR_CHECK(rmt_new_bytes_encoder(&bytes, &s_encoder));
    ESP_ERROR_CHECK(rmt_enable(s_chan));
}

void led_set(uint8_t r, uint8_t g, uint8_t b)
{
    uint8_t grb[3] = {g, r, b};
    rmt_transmit_config_t tx = {.loop_count = 0};
    if (rmt_transmit(s_chan, s_encoder, grb, sizeof grb, &tx) == ESP_OK) {
        rmt_tx_wait_all_done(s_chan, 10);
    }
}
