# Breadboard wiring: ESP32-S3-DevKitC-1 and 74AHCT125

This is the standard layout for every ESP32-S3-DevKitC-1 that drives LEDs from
a breadboard. One board and one 74AHCT125 level shifter sit on two half-size
breadboards, with up to four data outputs. The map names every hole, because
the board's pin labels are hidden once the board is in a breadboard.

## Breadboard terms

A half-size breadboard has rows 1–30 and columns a–j. Columns a–e of one row
connect to each other, and columns f–j of one row connect to each other. A gap
separates e and f. The rails along each long side run the full length.

**Always turn each breadboard so row 1 is farthest from you.** Column a must
then be on your left. If column a is on your right, stop: this map does not
apply to that breadboard.

## Layout

One board needs two breadboards: **A** for the ESP32 and **B** for the shifter.
Put B to the left of A.

## Outputs

Each connection names the pin and the hole the wire goes into.

| Output | Data jumper | Data out to the fixture's DIN |
|---|---|---|
| 1 | GPIO4 (A a4) → 1A (B a2) | 1Y (B a3) |
| 2 | GPIO5 (A a5) → 2A (B a5) | 2Y (B a6) |
| 3 | GPIO6 (A a6) → 3A (B j6) | 3Y (B j7) |
| 4 | GPIO7 (A a7) → 4A (B j3) | 4Y (B j4) |

In WLED (Config → LED Preferences), set each output's GPIO from this table.

**Unused outputs.** The shifter's unused inputs must not float. For each output
you don't use, skip its data jumper and connect its shifter input to the −
rail instead:

- Output 1: 1A (B d2) → left − rail.
- Output 2: 2A (B d5) → left − rail.
- Output 3: 3A (B g6) → right − rail.
- Output 4: 4A (B g3) → right − rail.

## Breadboard A: the ESP32

Turn the board so the antenna end is at row 1 and the USB ports point toward
row 30. Push the left header (J1) into column b and the right header (J3) into
column i, rows 1–22. The board covers columns c–h. Column a stays open beside
each J1 pin, and column j stays open beside each J3 pin. The USB cable leaves
past row 30.

Before you push the board in, check the printed labels against this table:
3V3 must be at the antenna end on the left.

| Row | Column b (J1) | Column i (J3) | Jumper from A |
|---|---|---|---|
| 1 | 3V3 | GND | — |
| 2 | 3V3 | TX (GPIO43) | — |
| 3 | RST | RX (GPIO44) | — |
| 4 | **GPIO4** | GPIO1 | output 1 |
| 5 | **GPIO5** | GPIO2 | output 2 |
| 6 | **GPIO6** | GPIO42 | output 3 |
| 7 | **GPIO7** | GPIO41 | output 4 |
| 8 | GPIO15 | GPIO40 | — |
| 9 | GPIO16 | GPIO39 | — |
| 10 | GPIO17 | GPIO38 (RGB LED) | — |
| 11 | GPIO18 | GPIO37 | — |
| 12 | GPIO8 | GPIO36 | — |
| 13 | GPIO3 | GPIO35 | — |
| 14 | GPIO46 | GPIO0 (BOOT) | — |
| 15 | GPIO9 | GPIO45 | — |
| 16 | GPIO10 | GPIO48 | — |
| 17 | GPIO11 | GPIO47 | — |
| 18 | GPIO12 | GPIO21 | — |
| 19 | GPIO13 | GPIO20 | — |
| 20 | GPIO14 | GPIO19 | — |
| 21 | 5V | GND | — (leave empty) |
| 22 | **GND** | GND | a22 → B left − rail |

## Breadboard B: the 74AHCT125

Turn the chip so its notch points toward row 1. Push it in across the gap with
pin 1 in e1. Pins 1–7 then run down column e, and pins 14–8 run down column f.
The enable pins (OE̅) are active-low, so they all go to the − rail.

| Row | Column e (pin) | Jumper | Column f (pin) | Jumper |
|---|---|---|---|---|
| 1 | 1 (1OE̅) | d1 → left − rail | 14 (VCC) | g1 → right + rail |
| 2 | 2 (1A) | a2 ← A a4 (GPIO4) | 13 (4OE̅) | g2 → right − rail |
| 3 | 3 (1Y) | a3 → output 1 DIN | 12 (4A) | j3 ← A a7 (GPIO7) |
| 4 | 4 (2OE̅) | d4 → left − rail | 11 (4Y) | j4 → output 4 DIN |
| 5 | 5 (2A) | a5 ← A a5 (GPIO5) | 10 (3OE̅) | g5 → right − rail |
| 6 | 6 (2Y) | a6 → output 2 DIN | 9 (3A) | j6 ← A a6 (GPIO6) |
| 7 | 7 (GND) | d7 → left − rail | 8 (3Y) | j7 → output 3 DIN |

Rails on B:

- One jumper joins the left − rail to the right − rail.
- The right + rail takes 5 V for the shifter (see Power).
- The left − rail takes the − of the LED supply.

## Power

- **Shifter VCC needs 4.5–5.5 V.** Feed the right + rail from a 5 V source:
  the LED supply when the LEDs run on 5 V, or a separate 5 V source when they
  run on 12 V or 24 V. Never put 12 V or 24 V on a breadboard.
- **Don't use the board's 5V pin (A row 21) for the shifter.** It is USB power
  after a diode, so it can sit below 4.5 V.
- **All grounds meet on B's − rail:** the ESP32 (A a22), the shifter, and the
  LED supply.
- **LED current never goes through a breadboard.** Connect each LED fixture's
  power and ground wires straight to its supply, through a fuse. Only the data
  wire (DIN) comes from B.

## Why this layout

- The header rows are 22.86 mm (0.9") apart: the board is 25.40 mm wide, and
  each row is 1.27 mm from its edge (Espressif,
  `DXF_ESP32-S3-DevKitC-1_V1.1_20220429.pdf`). On a breadboard, the rows can
  go in columns b and i, which leaves one open hole beside every pin.
- GPIO 4–7 are not strapping pins (0, 3, 45, 46), USB (19, 20), UART0
  (43, 44), octal PSRAM (35–37) or the RGB LED (38) (Espressif
  ESP32-S3-DevKitC-1 v1.1 user guide). They are also next to each other on J1.
- The 5V pin is USB VBUS after a Schottky diode (1N5819HW, D1 in the Espressif
  v1.1 schematic). The 74AHCT125 needs VCC 4.5–5.5 V, and its unused inputs
  must be held at VCC or GND (TI SCLS264R, §5.2).
- 74AHCT125 pin numbers are from TI SCLS264R, Table 4-1.

## Capture node: ESP32-S3-DevKitC-1 and PCM1808 (line in)

The line-in capture node (`firmware/audio-node`, docs/audio.md §8) uses
breadboard A alone, laid out as above, and no shifter. The PCM1808 module
stays off the breadboard: female-to-male jumpers go from its header pins,
by their printed labels, to holes in column a of breadboard A. Labels
differ between module makers, so match each by its function in the table.

| Module pin | Wire | Board pin (hole on A) |
|---|---|---|
| SCK or SCKI (system clock) | ← | GPIO15 (A a8) |
| BCK (bit clock) | ← | GPIO16 (A a9) |
| LRC or LRCK (word clock) | ← | GPIO17 (A a10) |
| OUT or DOUT (data) | → | GPIO18 (A a11) |
| 3.3V or VDD (digital supply) | ← | 3V3 (A a1) |
| 5V or VCC (analog supply) | ← | 5V (A a21) |
| GND | ← | GND (A a22) |
| FMT | ← | GND (A j22) |
| MD0 | ← | GND (A j21) |
| MD1 | ← | GND (A j1) |

- **FMT, MD0 and MD1 go low:** I2S format, and slave mode, so the ESP32
  makes the clocks (TI SLES177B, Tables 2 and 3). The chip pulls them low
  through 50 kΩ itself, but a module may pull them up, so wire them. Set
  them before power-on: the chip reads them only then.
- **Power comes from USB.** VDD takes 2.7–3.6 V and VCC 4.5–5.5 V
  (SLES177B, Recommended Operating Conditions). The 5V pin is USB VBUS
  after a Schottky diode (see Power), so measure it with the node running:
  below 4.5 V, use a better USB supply. A module with its own regulator may
  take 5 V only; then leave its 3.3V pin open.
- **The input:** the module's jack or its L/R pins. Feed it the mixer's
  REC or booth output (−10 dBV); a +4 dBu output clips it (RA-28 §7).
- **Ports:** flash and read logs on the UART port; `python -m pewpew wifi`
  talks to the node on the USB port, as it does to a WLED board.

Why these pins: GPIO15–18 sit in rows 8–11 of J1, next to each other, and
none is a strapping, USB, UART0, octal PSRAM or RGB LED pin (as for
GPIO4–7 above). The RGB LED (GPIO38) shows the node's state, and the BOOT
button (GPIO0) forces an I2S overflow for the bench (docs/audio.md §9).
