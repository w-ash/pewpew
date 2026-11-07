/*
 * Capture: the PCM1808 over I2S standard RX, as packets of 480 mono s16
 * samples (wire.h).
 *
 * The node is the I2S master: MCLK 256 fs (12.288 MHz), BCLK 64 fs and
 * 32-bit slots, so the BCLK divider is 4, a whole number (ADR-009,
 * "capture nodes"). The PCM1808 runs in slave mode (MD0, MD1 low) with
 * I2S format (FMT low) and sends 24 bits at the top of each slot. A
 * packet sample is the mean of the left and right channels, cut to its
 * top 16 bits.
 *
 * The sample index counts every sample the converter made since boot. When
 * the driver's receive queue is full it drops its oldest buffer and calls
 * `on_overflow` with the dropped size; the task adds those samples to the
 * index before it reads on and sets the overflow flag, so the host sees a
 * gap of the dropped length [inf: the gap sits within one DMA buffer of
 * where it was dropped]. A drop inside a packet ends the packet early.
 *
 * Sending never blocks this task: a packet goes to the stream task's
 * queue without waiting, and a full queue drops it.
 *
 * Holding BOOT (GPIO0) stalls the reader once for STALL_MS, which forces
 * an overflow for the attended bench (docs/audio.md).
 */
#include <string.h>

#include "driver/gpio.h"
#include "driver/i2s_std.h"
#include "esp_attr.h"
#include "esp_log.h"
#include "esp_task_wdt.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "node.h"

#define PIN_MCLK GPIO_NUM_15
#define PIN_BCLK GPIO_NUM_16
#define PIN_WS GPIO_NUM_17
#define PIN_DIN GPIO_NUM_18
#define PIN_STALL GPIO_NUM_0

#define DMA_FRAMES 240 /* 5 ms a DMA buffer */
#define DMA_BUFFERS 6
#define FRAME_BYTES 8 /* two 32-bit slots */
#define READ_TIMEOUT_MS 100
#define STALL_MS 100
#define CLIP_LEVEL 0x7FFF0000 /* a slot at or past this is a clipped 24-bit sample */

static const char *TAG = "capture";
static i2s_chan_handle_t s_rx;
static _Atomic uint32_t s_dropped; /* frames dropped and not yet counted into the index */

static bool IRAM_ATTR on_overflow(i2s_chan_handle_t handle, i2s_event_data_t *event, void *ctx)
{
    atomic_fetch_add_explicit(&s_dropped, (uint32_t)(event->size / FRAME_BYTES), memory_order_relaxed);
    return false;
}

static void put_le64(uint8_t *p, uint64_t v)
{
    for (int i = 0; i < 8; i++) {
        p[i] = (uint8_t)(v >> (8 * i));
    }
}

/* Hand `n` samples starting at sample `first` to the stream task. */
static void emit(node_packet_t *pkt, uint16_t n, uint64_t first, uint8_t flags)
{
    if (n == 0 || !atomic_load(&g_node.streaming)) {
        return;
    }
    memcpy(pkt->data, PP_AUDIO_MAGIC, 2);
    pkt->data[2] = PP_VERSION;
    pkt->data[3] = flags;
    put_le64(pkt->data + 4, first);
    put_le64(pkt->data + 12, g_node.nonce);
    pkt->samples = n;
    if (xQueueSend(g_node.packets, pkt, 0) != pdTRUE) {
        atomic_fetch_add(&g_node.queue_full, 1);
    }
}

static void capture_task(void *arg)
{
    static int32_t frames[DMA_FRAMES * 2];
    static node_packet_t pkt;
    uint64_t index = 0; /* the index of the next sample read */
    uint64_t first = 0; /* the index of the packet's first sample */
    uint16_t n = 0;
    uint8_t flags = 0;
    uint32_t peak = 0, counted = 0;
    bool stalled = false;
    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
    for (;;) {
        if (gpio_get_level(PIN_STALL) == 0) {
            if (!stalled) {
                stalled = true;
                vTaskDelay(pdMS_TO_TICKS(STALL_MS));
            }
        } else {
            stalled = false;
        }
        uint32_t dropped = atomic_exchange(&s_dropped, 0);
        if (dropped > 0) {
            emit(&pkt, n, first, flags);
            n = 0;
            flags = 0;
            index += dropped;
            atomic_fetch_add(&g_node.overflows, 1);
            atomic_fetch_add(&g_node.overflow_samples, dropped);
            flags |= PP_FLAG_OVERFLOW;
        }
        size_t got = 0;
        if (i2s_channel_read(s_rx, frames, sizeof frames, &got, READ_TIMEOUT_MS) != ESP_OK) {
            /* No watchdog reset: a reader that never reads panics the board (ADR-019). */
            ESP_LOGW(TAG, "I2S read timed out");
            continue;
        }
        esp_task_wdt_reset();
        uint8_t *out = pkt.data + PP_HEADER_SIZE;
        for (size_t i = 0; i < got / FRAME_BYTES; i++) {
            int32_t l = frames[2 * i], r = frames[2 * i + 1];
            if (l >= CLIP_LEVEL || l <= -CLIP_LEVEL || r >= CLIP_LEVEL || r <= -CLIP_LEVEL) {
                flags |= PP_FLAG_CLIP;
                atomic_fetch_add(&g_node.clips, 1);
            }
            int16_t s = (int16_t)(((int64_t)l + r) >> 17);
            uint32_t mag = s < 0 ? (uint32_t)(-(int32_t)s) : (uint32_t)s;
            peak = mag > peak ? mag : peak;
            if (++counted == PP_RATE) {
                atomic_store(&g_node.peak, peak);
                peak = 0;
                counted = 0;
            }
            if (n == 0) {
                first = index;
            }
            out[2 * n] = (uint8_t)s;
            out[2 * n + 1] = (uint8_t)((uint16_t)s >> 8);
            index++;
            if (++n == PP_SAMPLES) {
                emit(&pkt, n, first, flags);
                n = 0;
                flags = 0;
            }
        }
    }
}

void capture_start(void)
{
    gpio_config_t stall = {
        .pin_bit_mask = 1ULL << PIN_STALL,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&stall));

    i2s_chan_config_t chan = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    chan.dma_desc_num = DMA_BUFFERS;
    chan.dma_frame_num = DMA_FRAMES;
    ESP_ERROR_CHECK(i2s_new_channel(&chan, NULL, &s_rx));
    i2s_std_config_t std = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(PP_RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT, I2S_SLOT_MODE_STEREO),
        .gpio_cfg = {
            .mclk = PIN_MCLK,
            .bclk = PIN_BCLK,
            .ws = PIN_WS,
            .dout = I2S_GPIO_UNUSED,
            .din = PIN_DIN,
        },
    };
    std.clk_cfg.mclk_multiple = I2S_MCLK_MULTIPLE_256;
    std.slot_cfg.slot_bit_width = I2S_SLOT_BIT_WIDTH_32BIT;
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(s_rx, &std));
    i2s_event_callbacks_t callbacks = {.on_recv_q_ovf = on_overflow};
    ESP_ERROR_CHECK(i2s_channel_register_event_callback(s_rx, &callbacks, NULL));
    ESP_ERROR_CHECK(i2s_channel_enable(s_rx));
    /* Core 1, away from the Wi-Fi tasks on core 0. */
    xTaskCreatePinnedToCore(capture_task, "capture", 4096, NULL, 20, NULL, 1);
}
