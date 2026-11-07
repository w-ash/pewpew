idf_component_register(
    SRCS "main.c" "capture.c" "stream.c" "info.c" "improv.c" "led.c" "sub.c" "sha256.c"
    INCLUDE_DIRS "."
    PRIV_REQUIRES
        esp_app_format esp_driver_gpio esp_driver_i2s esp_driver_rmt esp_driver_usb_serial_jtag esp_event
        esp_http_server esp_hw_support esp_netif esp_timer esp_wifi lwip nvs_flash
)
