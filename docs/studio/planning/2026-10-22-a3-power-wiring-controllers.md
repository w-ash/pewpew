# A3. LED power, wiring and controller modeling (Explore agent, default model, 2026-10-22)

Brief: power estimation models; PSU sizing and fusing; voltage drop and injection; data-line limits
and pixels per output; existing tools and what they compute.

I could confirm most of what you asked with numbers. Three findings matter most for the plan:

- **Your bars may draw the same power no matter what they show.** QuinLED's closest measured match to your bars (24 V SK6812, one IC per LED, 60/m) draws a flat 52.70 W per 5 m with LEDs off, full white or any effect, labelled "Always uses max power".
- **The Falcon F16v5 may not suit 24 V pixels.** Its product page rates both power inputs at 5–13 VDC.
- **The "ZigData" receiver and any xLights power estimate were not found.**

Citation keys like [W2](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp) point to the source list at the end. Sources marked OLD are more than about 12 months old.

**1. Power estimation**
- **WLED v16.0.1 [W2](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp), [W3](https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.h), [W4](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h):**
  - Per frame it sums r+g+b+w after brightness is applied: `I_mA = colorSum × mA_per_LED / (4×255 for RGBW, 3×255 for RGB) + 1 mA × LEDs`. The board adds `MA_FOR_ESP` = 120 mA.
  - So the "mA per LED" setting means the current at full R+G+B+W.
  - The default is 55 mA; the WS2815 option is a special mode (stored as 255) that counts 12 mA × the brightest channel.
- **FastLED 3.10.8 (2026-10-18) [F1](https://github.com/FastLED/FastLED/blob/3.10.8/src/power_mgt.h):**
  - `Σ(channel × mW_channel) >> 8` plus `dark_mW × N` plus 125 mW for the MCU, with an optional exponent for non-linear response.
  - The RGBW default is R90 G70 B90 W100 dark 5 mW, at 5 V.
  - `setMaxPowerInVoltsAndMilliamps` lowers brightness until the estimate fits the budget.
- **Measured 24 V strips, 5 m each (QuinLED v1.07, 2024-12-01, OLD) [Q1](https://quinled.info/wp-content/uploads/2020/03/LED-power-table_24v_v1.07b.png):**

| Strip | LEDs off | Full RGB+W | Rainbow 100% |
|---|---|---|---|
| WS2814, 1 IC per 6 LEDs, 60/m | 8.35 W | 84.17 W | 26.52 W |
| SK6812, 1 IC per 6 LEDs | 5.46 W | 58.65 W | not measured |
| SK6812, one IC per LED (closest to your bars) | 52.70 W | 52.70 W | 52.70 W |

- **What those numbers imply (inference):**
  - WS2814 is about 1.68 W (70 mA) per zone at full white, and Rainbow is about 31% of full.
  - If your bars match the SK6812 one-IC-per-LED row, each 64-pixel bar is about 11.2 W (0.47 A) whatever it displays.
  - Measuring one bar with LEDs off and at full white decides which model applies.
- **Chip ratings:** WS2814 outputs are 16 mA × 4 channels [D2](https://www.lcsc.com/blog/introduction-to-worldsemi-led-driver-ic/). The OPSCO SKC6812RGBW datasheet gives R/G/B 8 mA and W 16.5 mA at 5 V [D3](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2308161144_OPSCO-Optoelectronics-SKC6812RGBW-BW_C5181320.pdf), OLD; seen only in a search excerpt.
- **Vendor W/m:** 14.4 W/m (SK6812 24 V, 1 IC per 6 LEDs) [V1](https://www.superlightingled.com/24v-builtin-sk6812-ic-6led-addressable-rgbw-6000k-lights-strip-p-7305.html); 17.5 W/m (24 V-to-5 V RGBW, 60/m) [V2](https://www.superlightingled.com/24v-to-5v-sk6812-individual-addressable-5050-rgb-rgbw-led-strips-6084-ledsm-p-5408.html).
- **Per-effect method (inference):** sum the linear channel values each frame with WLED's formula, then scale by measured full-white versus off figures from your bar.

**2. Power supplies and fusing**
- **Mean Well 24 V units:**

| Model | Current | Notes | Source |
|---|---|---|---|
| LRS-350-24 | 14.6 A / 350.4 W | 21.6–28.8 V adjust, 88% efficient, overload hiccup at 110–140% | [P1](https://www.meanwell.com/Upload/PDF/LRS-350/LRS-350-SPEC.PDF) datasheet 2025-09-12, borderline OLD |
| HLG-320H-24 | 13.34 A | | [P2](https://azcus.digikey.com/en/products/detail/mean-well-usa-inc/HLG-320H-24/7704031) [link not verified] |
| UHP-500-24 | 20.9 A | | [P3](https://nl.farnell.com/mean-well/uhp-500-24/power-supply-ac-dc-24v-20-9a/dp/3002734) |
| UHP-750-24 | 31.3 A | inference: I paired the series lists by wattage | [P3](https://nl.farnell.com/mean-well/uhp-500-24/power-supply-ac-dc-24v-20-9a/dp/3002734) |
| UHP-1000-24 | 42 A | same inference | [P3](https://nl.farnell.com/mean-well/uhp-500-24/power-supply-ac-dc-24v-20-9a/dp/3002734) |
| HLG-600H-24 | not found | | |

- **Headroom:**
  - Common practice is to run a supply at about 80%, i.e. PSU ≥ load ÷ 0.8 [N1](https://flexfireleds.com/blog/LED-power-supply-derating).
  - The NEC rule for continuous loads is 125% (210.20(A)) [N1](https://flexfireleds.com/blog/LED-power-supply-derating).
  - WLED itself shows "required" as `ceil((100 + Σ mA)/500)/2` A, and roughly a third of that "for most effects" [W5](https://github.com/wled/WLED/blob/v16.0.1/wled00/data/settings_leds.htm).
- **Fusing (QuinLED Dig-Octa Power-7) [Q5](https://quinled.info/quinled-dig-octa-power-7-power-handling):** 10 A maximum fuse per output, 240 W per output at 24 V, 50 A per board. An edge injection draws about 4 A and a middle injection about 8 A; the kit ships 5 A and 10 A ATO fuses for these.
- **Copper wire, 20 °C [A1](https://en.wikipedia.org/wiki/American_wire_gauge) (revision 2026-10-21):**

| AWG | Resistance (mΩ/m) | Ampacity 60/75 °C |
|---|---|---|
| 22 | 52.96 | 3/7 A |
| 20 | 33.31 | 5/11 A |
| 18 | 20.95 | 10/14 A |
| 16 | 13.17 | 12/16 A |
| 14 | 8.29 | 15/20 A |
| 12 | 5.21 | 20/25 A |

- **Class 2:** 100 VA limit, which is about 4.16 A at 24 V [C1](https://www.superbrightleds.com/blog/is-there-a-difference-between-class-2-and-class-ii-power-supplies.html), [C2](https://www.ecmweb.com/national-electrical-code/code-basics/article/20888526/classifying-and-using-c). I could not find the text of NEC Table 11(B) itself. If your bars are about 11 W, that is roughly 8 bars per Class 2 supply (inference).

**3. Voltage drop**
- **Lead drop:** `ΔV = I × 2 × L_one-way × R/m` [A5](https://slicker.me/wled/voltage-injection-math.html). LEDCO's chart works out the same way: 120 W, 16 AWG, 60 ft gives 2.4 V, which is 10% (my check) [A3](https://ledco.ca/en/category/voltage-drop-chart-12v-24v).
- **Drop along a strip:**
  - Fed at one end: `I/m × R/m × L²/2`; fed at both ends: `/8` [A4](https://www.diysmarthomehub.com/?p=18747) (2026-07-27).
  - As a sum over pixels: `R_seg × I × N(N+1)/2` [A5](https://slicker.me/wled/voltage-injection-math.html).
- **Acceptable drop:**
  - 3% for critical circuits and 10% for non-critical (ABYC, via Blue Sea) [A2](https://www.bluesea.com/support/reference/535/Voltage_Drop_in_Conductor_-_Wire_Sizing_Chart) [link not verified].
  - QuinLED allows 10% on injection wires [Q2](https://quinled.info/the-ultimate-led-strip-power-injection-guide/).
  - 3% for colour-critical work, 5–8% for accent lighting [A4](https://www.diysmarthomehub.com/?p=18747).
- **24 V injection rules of thumb:**
  - WS2814: 5 and 10 m are easy, 15 m needs a second feed at the end, 20 m is "on the edge", 30 m needs triple injection [Q3](https://quinled.info/dig-next-2-wiring-guide/).
  - QuinLED's 24 V table suggests front plus end injection every 2 strips (10 m) [Q1](https://quinled.info/wp-content/uploads/2020/03/LED-power-table_24v_v1.07b.png).
- **Daisy-chained bars (inference):** the drop at bar k is `Σ_{j≤k} R_j × I_bar × (n−j+1)`, where R_j is the round-trip resistance of jumper j plus the bar's own rail. Example: 10 bars at 0.47 A on 0.5 m 18 AWG jumpers lose about 0.54 V (2.3%) before counting the bars' rails. GND drop also shifts the data reference.

**4. Data signal**
- **SK6812 timing [D1](https://signliteled.com/wp-content/uploads/2024/08/SK6812-Datasheet.pdf), OLD:** 1.25 µs per bit (±600 ns), reset ≥ 80 µs, 32 bits per RGBW pixel = 40 µs.
- **Pixels per output (inference):** `N_max = (1/fps − 80 µs)/40 µs`.

| Frame rate | Max pixels | Whole 64-pixel bars |
|---|---|---|
| 30 fps | 831 | 12 (768 px) |
| 40 fps | 623 | 9 |
| 60 fps | 414 | 6 |

  QuinLED's figures agree: 595 pixels at 42 fps and 416 at 60 fps, with no reset time included [Q8](https://quinled.info/2021/03/23/max-amount-of-addressable-leds/), OLD.
- **WLED v16 limits [W4](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h), [W5](https://github.com/wled/WLED/blob/v16.0.1/wled00/data/settings_leds.htm), [W7](https://kno.wled.ge/features/multi-strip/):**
  - ESP32-S3 has 4 RMT outputs plus 8 LCD parallel outputs (12 total), and parallel output does not allow mixed LED types.
  - 2,048 LEDs per bus, 16,384 total, 192 KB of LED memory on the S3.
  - The settings page warns above 800 LEDs per output.
  - A 600-per-bus limit for parallel output appeared only in PR #5267, which was closed without merging [W9](https://github.com/wled/WLED/pull/5267).
  - WLED's docs give classic ESP32 throughput as 65k–85k LEDs/s [W7](https://kno.wled.ge/features/multi-strip/). At 40 fps that is about 1,600–2,100 pixels per board (inference). I found no S3 figure.
  - QuinLED says one Dig-Octa runs about 2,000 pixels under WLED at more than 40 fps [Q6](https://quinled.info/quinled-dig-octa-system-specific-example-configurations/).
- **Over the network:** WLED recommends at most 3 E1.31 universes (510 RGB LEDs) for 40 fps [W8](https://kno.wled.ge/interfaces/e1.31-dmx/). For RGBW that is about 384 pixels (inference).
- **Controller to first pixel:**
  - With a level shifter, 10–15 m can usually be made to work. Use 33 Ω when data and GND are tightly coupled and 249 Ω for separate wires; go differential beyond that [Q4](https://quinled.info/data-signal-cable-conditioning/).
  - Older forum reports: 8–12 m with 330 Ω plus a sacrificial pixel [X6](https://wled.discourse.group/t/esp32-sn74ahct125n-wiring-max-length-data-cable-to-sk6812/2294), 2021, OLD.
  - I found no official 74AHCT125 length limit.
- **Between fixtures:** about 3 m before planning null pixels; the 10 m datasheet figure is optimistic [X5](https://auschristmaslighting.com/threads/maximum-distance-between-ws2811-pixel-nodes.7607), undated.
- **Differential options:** WS281x usually needs boosting beyond 50–70 ft, and a differential receiver reaches about 300 ft [X4](https://www.tindie.com/products/k7bbr/wasatch-pixels-differential-receiver/). QuinLED Diff-Adv reaches 500 m over CAT5e [Q7](https://quinled.info/quinled-diff-adv-distance-guide/).
- **Controller limits:**
  - F16v5: 1,024 pixels per output, 16 outputs plus 4 SmartReceiver ports (up to 32), e-fuses with no rating given, power inputs 5–13 VDC [X2](https://pixelcontroller.com/store/featured/88-f16v5.html). The page title says F16V4 but the specs are for the F16v5.
  - The community wiki matches, but it says it has not been reviewed [X3](https://auschristmaslighting.com/wiki/Falcon-F16v5), 2025-01, OLD.

**5. Existing tools**
- **xLights Controller Visualizer [X1](https://manual.xlights.org/xlights/chapters/chapter-four-set-up/lighting-networks/controller-visualizer.md):** drag models onto ports, set smart-receiver IDs A–F, cascade, set brightness, print, export CSV, and see configuration errors. No power estimate turned up in the manual or a GitHub code search.
- **WLED [W5](https://github.com/wled/WLED/blob/v16.0.1/wled00/data/settings_leds.htm), [W6](https://github.com/wled/WLED/blob/3cdb5108b924ec26dec81d2c92962b70b185bd01/wled00/data/index.js):** required PSU amps, RMT/I2S channels used, memory warnings, and "Estimated current" plus "Average FPS" in the Info panel.
- **QuinLED sheets [Q1](https://quinled.info/wp-content/uploads/2020/03/LED-power-table_24v_v1.07b.png):** measured watts per effect and injection suggestions.
- **diysmarthomehub calculator [A4](https://www.diysmarthomehub.com/?p=18747):** outputs feed spacing, number of feed points, amps/watts, worst-case voltage and wire resistances.
- **Advatek:** listing gives 1,020 RGB pixels per output [X7](https://www.ultraleds.co.uk/advatek-pixlite-a4-s-mk3-led-pixel-controller). The Assistant tool's power features were not found.
- **Which outputs users value most:** I found no survey. Inference from what the tools converge on: pixels per port, amps per port against the fuse, injection points, worst-case voltage and PSU load.

I searched no local files. While fetching, the web tool saved the LRS-350 PDF and the QuinLED PNG into its own folder under `~/.claude/projects/.../tool-results/`; I didn't create any other files.

## Sources

- W1 https://github.com/wled/WLED/releases/tag/v16.0.1 (2026-07-07)
- W2 https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.cpp
- W3 https://github.com/wled/WLED/blob/v16.0.1/wled00/bus_manager.h
- W4 https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h
- W5 https://github.com/wled/WLED/blob/v16.0.1/wled00/data/settings_leds.htm
- W6 https://github.com/wled/WLED/blob/3cdb5108b924ec26dec81d2c92962b70b185bd01/wled00/data/index.js (main branch, pinned to commit 3cdb510)
- W7 https://kno.wled.ge/features/multi-strip/
- W8 https://kno.wled.ge/interfaces/e1.31-dmx/
- W9 https://github.com/wled/WLED/pull/5267
- F1 https://github.com/FastLED/FastLED/blob/3.10.8/src/power_mgt.h and https://github.com/FastLED/FastLED/blob/3.10.8/src/power_mgt.cpp.hpp (FastLED 3.10.8)
- Q1 https://quinled.info/wp-content/uploads/2020/03/LED-power-table_24v_v1.07b.png
- Q2 https://quinled.info/the-ultimate-led-strip-power-injection-guide/
- Q3 https://quinled.info/dig-next-2-wiring-guide/
- Q4 https://quinled.info/data-signal-cable-conditioning/
- Q5 https://quinled.info/quinled-dig-octa-power-7-power-handling
- Q6 https://quinled.info/quinled-dig-octa-system-specific-example-configurations/
- Q7 https://quinled.info/quinled-diff-adv-distance-guide/
- Q8 https://quinled.info/2021/03/23/max-amount-of-addressable-leds/
- D1 https://signliteled.com/wp-content/uploads/2024/08/SK6812-Datasheet.pdf
- D2 https://www.lcsc.com/blog/introduction-to-worldsemi-led-driver-ic/
- D3 https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2308161144_OPSCO-Optoelectronics-SKC6812RGBW-BW_C5181320.pdf
- V1 https://www.superlightingled.com/24v-builtin-sk6812-ic-6led-addressable-rgbw-6000k-lights-strip-p-7305.html
- V2 https://www.superlightingled.com/24v-to-5v-sk6812-individual-addressable-5050-rgb-rgbw-led-strips-6084-ledsm-p-5408.html
- P1 https://www.meanwell.com/Upload/PDF/LRS-350/LRS-350-SPEC.PDF
- P2 https://azcus.digikey.com/en/products/detail/mean-well-usa-inc/HLG-320H-24/7704031 [link not verified]
- P3 https://nl.farnell.com/mean-well/uhp-500-24/power-supply-ac-dc-24v-20-9a/dp/3002734 and https://www.directindustry.com/product-manufacturer/mean-well-power-supply-60871-135233.html [link not verified]
- N1 https://flexfireleds.com/blog/LED-power-supply-derating and https://forums.mikeholt.com/threads/80-rule-residential.115888/latest [link not verified]
- C1 https://www.superbrightleds.com/blog/is-there-a-difference-between-class-2-and-class-ii-power-supplies.html
- C2 https://www.ecmweb.com/national-electrical-code/code-basics/article/20888526/classifying-and-using-c
- A1 https://en.wikipedia.org/wiki/American_wire_gauge (revision 2026-10-21)
- A2 https://www.bluesea.com/support/reference/535/Voltage_Drop_in_Conductor_-_Wire_Sizing_Chart [link not verified]
- A3 https://ledco.ca/en/category/voltage-drop-chart-12v-24v
- A4 https://www.diysmarthomehub.com/?p=18747 (2026-07-27)
- A5 https://slicker.me/wled/voltage-injection-math.html
- X1 https://manual.xlights.org/xlights/chapters/chapter-four-set-up/lighting-networks/controller-visualizer.md
- X2 https://pixelcontroller.com/store/featured/88-f16v5.html
- X3 https://auschristmaslighting.com/wiki/Falcon-F16v5
- X4 https://www.tindie.com/products/k7bbr/wasatch-pixels-differential-receiver/
- X5 https://auschristmaslighting.com/threads/maximum-distance-between-ws2811-pixel-nodes.7607
- X6 https://wled.discourse.group/t/esp32-sn74ahct125n-wiring-max-length-data-cable-to-sk6812/2294
- X7 https://www.ultraleds.co.uk/advatek-pixlite-a4-s-mk3-led-pixel-controller

Note added by the orchestrator: for the 1M LED Pixel Bar, the fixture record gives Clen's figure of
25.6 W max per bar (the maintainer's fixture notes, INV-001 and RES-038,
https://www.clenled.com/bar/rgbw-led-pixel-bar.html). That replaces the 11.2 W inference above as
the default. One bar's real draw is still unmeasured.

**Added by the link pass:**
- The maintainer's fixture notes (fixture record, not public; in the orchestrator note)
