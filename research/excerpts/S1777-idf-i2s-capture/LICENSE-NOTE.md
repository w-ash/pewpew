# Excerpt provenance — S1777 ESP-IDF I2S receive overflow and clock

- project: ESP-IDF
- license: Apache-2.0 (upstream LICENSE)
- copyright: Espressif Systems (Shanghai) CO LTD
- pinned: espressif/esp-idf@0e6b480f858c69862ffb6001d96e9eef74599a6e
- paths / contents (fetched at the pin on 2026-11-06):
  - `components/esp_driver_i2s/i2s_common.c` lines 940–948 (L943–946: a full receive queue drops
    its oldest buffer and calls `on_recv_q_ovf`) and lines 1963–1995 (L1965–1993: the master clock
    is divided fractionally, `integer + numerator/denominator`).
  - `components/esp_driver_i2s/include/driver/i2s_types.h` lines 64–77 (L72–75: the event's `size`
    is also the size dropped on a queue overflow).
  - `components/soc/esp32s3/include/soc/clk_tree_defs.h` lines 325–341 (L327–340: the S3's I2S clock
    sources are PLL_F240M, PLL_F160M, XTAL and external; no APLL).
- why excerpted: ADR-009's 2026-11-06 amendment "capture nodes": the node counts dropped samples
  into its sample index, and the host measures drift rather than assuming it.

Licence text: `../LICENSES/Apache-2.0.txt`. Upstream file headers at the pin:
`i2s_common.c` "SPDX-FileCopyrightText: 2015-2026 Espressif Systems (Shanghai)
CO LTD", `i2s_types.h` "2020-2026", `clk_tree_defs.h` "2022-2026" and licensed
"Apache-2.0 OR MIT". The upstream repo has no NOTICE file at the pin.
