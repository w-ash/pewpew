---
name: setting-up-wled-boards
description: Walks a person through setting up a new ESP32-S3-DevKitC-1 board as a stock WLED 16.0.1 node for pewpew on a Mac, from plugging it in to a verified IP. Covers finding the serial port, flashing at install.wled.me (which build to pick), setting its Wi-Fi and a unique name with `python -m pewpew wifi`, and checking the result. Use when someone has a new or blank board, wants to flash or reflash WLED, needs to put a board on Wi-Fi or rename it, or asks for a board's IP before wiring or a bench test.
---

# Setting up a WLED board

Setup ends with a board that runs WLED 16.0.1, is on a known Wi-Fi network,
has a unique name (`pewpew-1`, `pewpew-2`, ...) and has an IP you have
checked. pewpew addresses a board by its IPv4 address or by its mDNS name
(`pewpew-N.local`, in `--ddp` or the room map), so the name and the IP are
the deliverables.

## Rules

- **Only USB goes into the board.** No jumpers on its pins, nothing on the 5V
  pin (J1-21, hole A a21 on a breadboard), and the bench supply stays off.
  Setup needs no wiring, and a stray wire can damage the board or a bar.
- **Name every connection by pin name and breadboard hole,** for example
  "GPIO4 (A a4) → 1A (B a2)", per CLAUDE.md "Wiring instructions" and the
  map in `docs/breadboard-wiring.md`.
- **The person does the physical steps, and the Wi-Fi password never enters
  the chat.** Stop and ask at each step marked 🧑. With `--keychain`, the
  `wifi` command reads the password from the macOS Keychain, and macOS asks
  the person to allow it, so you can run the command yourself. Without
  `--keychain`, it uses a hidden prompt, which only works in the person's own
  Terminal window, not through you or Claude Code's `!` prefix.
- **Writes to the board are tier-1 bench actuation** (CLAUDE.md T-7). Run
  `--dry-run` first. A real run appends a record to the audit log
  (`pewpew.audit`). Never point these steps at a deployed board (tier 2).
- **Give one step at a time,** with exact commands and each reason in one
  sentence.

## Board facts

- ESP32-S3-DevKitC-1-N8R8: 8 MB quad flash, 8 MB **octal** PSRAM (Adafruit
  #5336). It has two Micro-USB ports, labelled UART and USB.
- **Flash on the UART port, then talk to WLED on the USB port.** The UART
  port goes through a Silicon Labs CP2102N, needs no macOS driver, and
  appears as `/dev/cu.usbserial-*`. The chip's bootloader listens there, so
  flashing works. But the `8MB_opi` build puts WLED's serial link, Improv
  included, on the native USB port (`ARDUINO_USB_CDC_ON_BOOT=1`,
  `platformio.ini:636`). That port appears as `/dev/cu.usbmodem*`, named "USB
  JTAG_serial debug unit". Improv on the UART port gets `No Improv reply`.
- A new board runs Espressif's demo: one LED cycles colours, and the red
  power LED is solid.
- The WLED 16.0.1 build is `WLED_16.0.1_ESP32-S3_8MB_opi.bin`. Don't use
  `_8MB_qspi`, which is for quad PSRAM, or `_8MB_none`.

## Checklist

Copy this list and tick each item as you go:

```
- [ ] 1. Find the serial port
- [ ] 2. Flash WLED 16.0.1
- [ ] 3. Set the Wi-Fi and the name
- [ ] 4. Verify
- [ ] 5. Report
```

### 1. Find the serial port

Run `ls /dev/cu.*` and keep the output. 🧑 Ask the person to plug a
data-capable cable into the **UART** port. Run `ls /dev/cu.*` again. The new
`/dev/cu.usbserial-*` entry is the port. If no entry appears, the cable may
be charge-only.

### 2. Flash WLED 16.0.1

🧑 The person flashes in desktop Chrome or Edge, because Safari has no Web
Serial. At https://install.wled.me they set:

- Mode **Advanced**, version **16.0.1**, build **Plain**
- Flash size **8MB**, memory **PSRAM (S3 OPI)**, flash mode **Default**

Then **Install**, pick the port from step 1 (it is listed as "CP2102N USB to
UART Bridge Controller"), and turn on **Erase device** if offered. The colour
cycling stops when the flash is done. 🧑 Then they **close the tab**, because
Chrome can keep the port open and block step 3.

### 3. Set the Wi-Fi and the name

🧑 Ask the person to move the cable to the **USB** port. Run `ls /dev/cu.*`
again, and use the new `/dev/cu.usbmodem*` entry as the port in this step.
Pick the next free name. Ask which numbers are already taken, because nothing
on the network lists them. The Wi-Fi must be 2.4 GHz, because the ESP32-S3
has no 5 GHz radio. 🧑 Ask for the network's name: macOS hides it from
command-line tools. The Mac must have joined that network before, so that
its password is in the Keychain. Run the dry run, which checks the Keychain
item without reading it:

```sh
uv run python -m pewpew wifi /dev/cu.usbmodemXXXX --ssid "NAME" --keychain --name pewpew-N --dry-run
```

🧑 Tell the person that macOS will ask them to allow a Keychain read, then run
the same command without `--dry-run`. It prints `Board IP: <ip>`, sets the
name, and reboots the board. If it fails, see Troubleshooting below.
🧑 Ask them to mark the board with its number.

### 4. Verify

Wait about 10 s for the reboot, then run:

```sh
curl -s http://<ip>/json/info | python3 -c 'import json,sys; i=json.load(sys.stdin); print(i["ver"], i["name"], i["wifi"]["signal"])'
```

The output must be `16.0.1 pewpew-N <signal>`. If the IP doesn't answer, the
Mac may be on a different network from the board.

### 5. Report

Give the person the name, the IP and the signal. Recommend naming the board
as `pewpew-N.local` in the room map, because pewpew then follows it to a new
DHCP address after a power cycle. A DHCP reservation on the private router still
helps, because people open the board's own page by IP.
`uv run python -m pewpew boards scan` lists every WLED board on the network with
its IP, name and MAC.

### LED settings, if the task asks for them

The values (type, GPIO, length, colour order) come from the task's own guide.
For a board on breadboards, the GPIO for each output is in
`docs/breadboard-wiring.md`. Set them over the API with `curl`. A partial
`/json/cfg` keeps every setting it doesn't send (`cfg.cpp:170-252`). Print
the payload as a dry run, write an audit record (`pewpew.audit.record`),
then POST, reboot, and read `hw.led` back from `/json/cfg`:

```sh
curl -s -X POST http://<ip>/json/cfg -H 'Content-Type: application/json' -d '{"hw":{"led":{"maxpwr":0,"ins":[{"start":0,"len":64,"pin":[4],"order":0,"rev":false,"skip":0,"type":30,"ref":false,"rgbwm":0,"freq":0,"maxpwr":0,"ledma":55,"drv":0,"text":""}]}}}'
curl -s -X POST http://<ip>/json/state -H 'Content-Type: application/json' -d '{"rb":true}'
```

The keys: `type` 30 is SK6812/WS2814 RGBW, `order` 0 is GRB and 1 is RGB
(`const.h:372`), and `rgbwm` is auto-white (0 None, 1 Brighter, 2 Accurate).
`maxpwr` 0, both for the board and for the output, turns the brightness
limiter off (`cfg.cpp:242`). Set the target refresh rate, `hw.led.fps`, to
60 or more (`{"hw":{"led":{"fps":60}}}`): WLED's default of 42 is below
pewpew's DDP rate, so the board holds or drops frames, and `run`'s health
row warns about it. In the web UI the same fields are under Config
→ LED Preferences, with the labels "SK6812/WS2814 RGBW", "Length", "GPIO",
"Color Order", "Enable automatic brightness limiter", "Auto-calculate W
channel from RGB" and "Target refresh rate".

## Troubleshooting

| Output | Cause and fix |
|---|---|
| `Cannot open ...: Resource busy` | Another app holds the port. Close the install.wled.me tab and any serial monitor. |
| `No Improv reply` | The cable is in the UART port: move it to the USB port and use `/dev/cu.usbmodem*`. Otherwise WLED isn't running: repeat step 2. |
| `[Errno 65] No route to host` from Python while `curl http://<ip>/json/info` works | macOS Local Network privacy. It exempts only tools run from Apple's Terminal or over SSH, so Python in Ghostty or another terminal is judged by its own ad-hoc identity and is blocked (TN3179). This blocks pewpew's DDP output too. For now, set the name with `curl -X POST http://<ip>/json/cfg -H 'Content-Type: application/json' -d '{"id":{"name":"pewpew-N","mdns":"pewpew-N"}}'`, then reboot it (`/json/state`, `{"rb":true}`). Lasting fixes: the person runs `sudo defaults write com.apple.network.local-network AllowedWiFiLocalNetworkAddresses -array "<subnet>/24"` and restarts the Mac, or uses Terminal, or on macOS 27.2 or later removes and re-adds the app in the Local Network list. |
| `could not join the network` | Wrong password, or a 5 GHz-only network. Run step 3 again. |
| `No IP within 40 s` | The network is slow to hand out an address, or it's out of range. Rerun with `--timeout 90`. |
| `No Wi-Fi password for ... in the Keychain` | The name is spelled differently, the Mac never joined that network, or the person denied the read. Check the name, or have the person run the command without `--keychain` in their own Terminal. |
| `Lost the serial port` | The cable moved, or the board reset its USB. Reseat the cable and rerun step 3. |
| `Could not set the name` | The board joined, but the Mac can't reach it over HTTP. Check that both are on the same network, then rerun step 3. |
| `Press RST to apply the name` | The name is saved, but the reboot request failed. Press RST on the board. |

If `pewpew wifi` keeps failing, use the manual route. The board broadcasts a
Wi-Fi network named `WLED-AP` (password `wled1234`). Join it and open
`http://4.3.2.1` → **WIFI SETTINGS**. Set the name later in Config → WiFi
Setup (mDNS) and Config → User Interface (server description).

Sources: WLED v16.0.1 source (`wled00/improv.cpp`, `wled.cpp:536` and
`:942-978`, `cfg.cpp:55-56`, `data/settings_leds.htm`); the v16.0.1 release
assets; the Espressif DevKitC-1 v1.1 user guide; Adafruit #5336. The protocol
behaviour is described in the `pewpew.provision` docstring.
