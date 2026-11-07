# Third-party notices: pewpew audio node firmware

The source in this folder is Apache-2.0 (`LICENSE`), as pewpew is (ADR-012). A
built image (`build/pewpew-audio-node.bin`) also holds the code below. Ship
this file with any image you publish; flashing your own nodes publishes
nothing (RA-28 §6).

| Component | Version | Licence | Source |
|---|---|---|---|
| ESP-IDF (drivers, Wi-Fi, lwIP, HTTP server, NVS, FreeRTOS port) | v6.1 | Apache-2.0 | https://github.com/espressif/esp-idf |
| mdns | 1.15.1 | Apache-2.0 | https://github.com/espressif/esp-protocols (`components/mdns`) |
| Wi-Fi and PHY binary libraries (esp32-wifi-lib) | with IDF v6.1 | Apache-2.0 | https://github.com/espressif/esp32-wifi-lib |
| FreeRTOS kernel | with IDF v6.1 | MIT | via ESP-IDF |
| lwIP | with IDF v6.1 | BSD-3-Clause | via ESP-IDF |
| newlib | with IDF v6.1 | BSD and similar | via ESP-IDF |
| wpa_supplicant | with IDF v6.1 | BSD-3-Clause | via ESP-IDF |
| FreeBSD net80211 | with IDF v6.1 | BSD | via ESP-IDF |
| Mbed TLS | with IDF v6.1 | Apache-2.0 | via ESP-IDF |

The ESP-IDF copyrights page lists every licence in an image:
https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/COPYRIGHT.html
(RA-28 S1788). Apache-2.0 asks a redistributor to keep the components'
NOTICE files and licence texts; ESP-IDF keeps them in its source tree, and
`managed_components/espressif__mdns/LICENSE` comes with the mdns component.

The Improv serial handler (`main/improv.c`) and SHA-256 (`main/sha256.c`)
are pewpew's own, written from the Improv serial spec and FIPS 180-4, not
taken from the Improv SDK. No GPL or WLED code is in this folder.
