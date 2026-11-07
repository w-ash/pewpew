/*
 * pewpew's line-in capture node (RA-28 M2b; ADR-009, 2026-11-06 amendment
 * "capture nodes"): an ESP32-S3-DevKitC-1 with a PCM1808 that sends raw
 * 48 kHz mono audio to the one host that subscribed. It captures
 * (capture.c), streams and answers SUBs (stream.c), serves a read-only
 * `GET /json/info` (info.c) and speaks Improv on its USB port
 * (improv.c). It does no analysis and has no network update: it is
 * flashed over USB.
 *
 * Storage: the `nvs` partition holds the Wi-Fi settings and the names;
 * the `nodekey` partition holds the 32-byte key, written once with the
 * firmware from the image `python -m pewpew audio key MAC` makes
 * (docs/audio.md). A node with no key refuses every SUB.
 *
 * Resilience (ADR-019's subset for an attended node): the task watchdog
 * panics and reboots the board when a task stops (CONFIG_ESP_TASK_WDT_PANIC),
 * `/json/info` names the reset reason, and the supervisor here restarts
 * the board when a holder renews but nothing has been sent for STALL_MS.
 * The RGB LED is green while the node streams, blue while it is on the
 * network with no holder, and off without a network.
 */
#include <stdio.h>
#include <string.h>

#include "esp_attr.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_random.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "mdns.h"
#include "node.h"
#include "nvs.h"
#include "nvs_flash.h"

#define STALL_MS 5000
#define QUEUE_PACKETS 8 /* 80 ms of packets between the capture and stream tasks */
#define KEY_PARTITION "nodekey"
#define KEY_NAMESPACE "pewpew"
#define NAMES_NAMESPACE "node"
#define SEND_STALL 0x5354414c /* the supervisor's restart, kept across it */
#define SETTLE_MS 3000        /* how long a join waits for a connect attempt under way to end */
#define SETTLE_STEP_MS 100

static const char *TAG = "node";
static RTC_NOINIT_ATTR uint32_t s_restart;
static _Atomic bool s_switching; /* node_join changes the settings: no reconnect */

node_t g_node;

uint32_t node_ms(void) { return (uint32_t)(esp_timer_get_time() / 1000); }

bool node_valid_name(const char *name, size_t len)
{
    if (len == 0 || len > NODE_NAME_MAX || name[0] == '-' || name[len - 1] == '-') {
        return false;
    }
    for (size_t i = 0; i < len; i++) {
        char c = name[i];
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-')) {
            return false;
        }
    }
    return true;
}

/* Store and apply a new device name or hostname; NULL leaves one as it is. */
void node_set_names(const char *name, const char *hostname)
{
    nvs_handle_t nvs;
    bool stored = nvs_open(NAMES_NAMESPACE, NVS_READWRITE, &nvs) == ESP_OK;
    if (name != NULL) {
        strlcpy(g_node.name, name, sizeof g_node.name);
        mdns_instance_name_set(g_node.name);
        if (stored) {
            nvs_set_str(nvs, "name", g_node.name);
        }
    }
    if (hostname != NULL) {
        strlcpy(g_node.hostname, hostname, sizeof g_node.hostname);
        esp_netif_set_hostname(g_node.netif, g_node.hostname); /* for the next DHCP lease */
        mdns_hostname_set(g_node.hostname);
        if (stored) {
            nvs_set_str(nvs, "hostname", g_node.hostname);
        }
    }
    if (stored) {
        nvs_commit(nvs);
        nvs_close(nvs);
    }
}

static void load_names(void)
{
    char fallback[NODE_NAME_MAX + 1];
    snprintf(fallback, sizeof fallback, "pewpew-node-%02x%02x%02x", g_node.mac[3], g_node.mac[4], g_node.mac[5]);
    strlcpy(g_node.name, fallback, sizeof g_node.name);
    strlcpy(g_node.hostname, fallback, sizeof g_node.hostname);
    nvs_handle_t nvs;
    if (nvs_open(NAMES_NAMESPACE, NVS_READONLY, &nvs) == ESP_OK) {
        size_t size = sizeof g_node.name;
        if (nvs_get_str(nvs, "name", g_node.name, &size) != ESP_OK) {
            strlcpy(g_node.name, fallback, sizeof g_node.name);
        }
        size = sizeof g_node.hostname;
        if (nvs_get_str(nvs, "hostname", g_node.hostname, &size) != ESP_OK) {
            strlcpy(g_node.hostname, fallback, sizeof g_node.hostname);
        }
        nvs_close(nvs);
    }
}

/* The key from its own partition, or false when it holds none. */
static bool load_key(uint8_t key[PP_KEY_SIZE])
{
    nvs_handle_t nvs;
    if (nvs_flash_init_partition(KEY_PARTITION) != ESP_OK ||
        nvs_open_from_partition(KEY_PARTITION, KEY_NAMESPACE, NVS_READONLY, &nvs) != ESP_OK) {
        return false;
    }
    size_t size = PP_KEY_SIZE;
    bool found = nvs_get_blob(nvs, "key", key, &size) == ESP_OK && size == PP_KEY_SIZE;
    nvs_close(nvs);
    return found;
}

static const char *reset_reason(void)
{
    esp_reset_reason_t reason = esp_reset_reason();
    if (reason == ESP_RST_SW && s_restart == SEND_STALL) {
        s_restart = 0;
        return "send-stall";
    }
    s_restart = 0;
    switch (reason) {
    case ESP_RST_POWERON: return "poweron";
    case ESP_RST_EXT: return "ext";
    case ESP_RST_SW: return "sw";
    case ESP_RST_PANIC: return "panic";
    case ESP_RST_INT_WDT: return "int_wdt";
    case ESP_RST_TASK_WDT: return "task_wdt";
    case ESP_RST_WDT: return "wdt";
    case ESP_RST_DEEPSLEEP: return "deepsleep";
    case ESP_RST_BROWNOUT: return "brownout";
    case ESP_RST_SDIO: return "sdio";
    case ESP_RST_USB: return "usb";
    case ESP_RST_JTAG: return "jtag";
    case ESP_RST_EFUSE: return "efuse";
    case ESP_RST_PWR_GLITCH: return "pwr_glitch";
    case ESP_RST_CPU_LOCKUP: return "cpu_lockup";
    default: return "unknown";
    }
}

static void on_wifi(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        wifi_config_t cfg;
        if (esp_wifi_get_config(WIFI_IF_STA, &cfg) == ESP_OK && cfg.sta.ssid[0] != '\0') {
            esp_wifi_connect();
        }
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        atomic_store(&g_node.ip, 0);
        if (!atomic_load(&s_switching)) {
            esp_wifi_connect(); /* forever: the private router may come up after the node */
        }
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        const ip_event_got_ip_t *got = data;
        atomic_store(&g_node.ip, got->ip_info.ip.addr);
    }
}

/*
 * Join the network `cfg` names. esp_wifi_set_config refuses new settings
 * while the station connects (ESP_ERR_WIFI_STATE), so nothing reconnects
 * while they change, and an attempt already under way gets SETTLE_MS to
 * end. On a refusal the station goes back to the settings it had.
 */
esp_err_t node_join(wifi_config_t *cfg)
{
    atomic_store(&s_switching, true);
    atomic_store(&g_node.ip, 0);
    esp_wifi_disconnect();
    esp_err_t err = esp_wifi_set_config(WIFI_IF_STA, cfg);
    for (int waited = 0; err == ESP_ERR_WIFI_STATE && waited < SETTLE_MS; waited += SETTLE_STEP_MS) {
        vTaskDelay(pdMS_TO_TICKS(SETTLE_STEP_MS));
        err = esp_wifi_set_config(WIFI_IF_STA, cfg);
    }
    atomic_store(&s_switching, false);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "the station refused the new Wi-Fi settings: %s", esp_err_to_name(err));
    }
    esp_wifi_connect();
    return err;
}

static void start_wifi(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    g_node.netif = esp_netif_create_default_wifi_sta();
    esp_netif_set_hostname(g_node.netif, g_node.hostname);
    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, on_wifi, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, on_wifi, NULL));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE)); /* no DTIM sleep: SUBs and replies go at once (ADR-016) */
}

static void start_mdns(void)
{
    ESP_ERROR_CHECK(mdns_init());
    mdns_hostname_set(g_node.hostname);
    mdns_instance_name_set(g_node.name);
    mdns_service_add(NULL, "_http", "_tcp", 80, NULL, 0);
}

void app_main(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
    g_node.reset_reason = reset_reason();
    ESP_ERROR_CHECK(esp_read_mac(g_node.mac, ESP_MAC_WIFI_STA));
    load_names();
    static uint8_t key[PP_KEY_SIZE];
    g_node.has_key = load_key(key);
    if (!g_node.has_key) {
        ESP_LOGW(TAG, "no key in the %s partition: every SUB is refused (docs/audio.md)", KEY_PARTITION);
    }
    start_wifi();
    /* After the radio starts, so the random numbers come from its noise. */
    g_node.nonce = (uint64_t)esp_random() << 32 | esp_random();
    start_mdns();
    led_init();
    g_node.packets = xQueueCreate(QUEUE_PACKETS, sizeof(node_packet_t));
    stream_start(g_node.has_key ? key : NULL);
    capture_start();
    info_start();
    improv_start();
    ESP_LOGI(TAG, "%s %s up, reset reason %s", PP_FIRMWARE, g_node.hostname, g_node.reset_reason);

    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        bool streaming = atomic_load(&g_node.streaming);
        if (streaming) {
            led_set(0, 24, 0);
        } else if (atomic_load(&g_node.ip) != 0) {
            led_set(0, 0, 24);
        } else {
            led_set(0, 0, 0);
        }
        if (streaming && node_ms() - atomic_load(&g_node.last_send_ms) > STALL_MS) {
            ESP_LOGE(TAG, "a holder renews but nothing was sent for %d ms: restarting", STALL_MS);
            s_restart = SEND_STALL;
            esp_restart();
        }
    }
}
