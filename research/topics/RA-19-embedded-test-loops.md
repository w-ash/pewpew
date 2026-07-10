# RA-19: Embedded test loops (simulation, emulation, hardware-in-the-loop)

Last researched: 2026-07-09
Status: draft
S-ID block: S1100–S1149

## Key questions

- Can any emulator (Wokwi, QEMU-for-ESP32, Renode) exercise ESP-NOW/WiFi paths,
  or is the radio the hard boundary that forces sim-above / HIL-below?
- Wokwi in 2026: is `wokwi-cli` a maintained CI product, what does it cost, and
  which ESP32-S3 peripherals does it actually emulate (RMT? WiFi? ESP-NOW?)
- What does Espressif itself use to test ESP-IDF — pytest-embedded plugin
  family, Unity-on-target, hardware runners — and how mature is it for
  third-party projects?
- What are the established patterns for CI with attached hardware:
  self-hosted runners with USB devices, hardware labels, flake quarantine,
  artifact capture (serial logs, waveforms, pcaps)?
- Which instruments can a Python harness automate in 2026: sigrok/PulseView vs
  Saleae Logic 2, monitor-mode WiFi sniffers for ESP-NOW, Nordic PPK2,
  uhubctl-class USB power switching, photodiode/ADC flicker rigs?
- How should pewpew apply property-based testing (Hypothesis) and fuzzing
  (libFuzzer/AFL++) to the 11-byte codec, gossip merge, and PCO convergence in
  pure-Python simulation?
- What do multi-day soak tests look like as background CI jobs with automated
  triage?
- What is the concrete bench BOM (~$200 vs ~$500) + software stack that makes
  architecture §12's 20 prototype-to-verify items repeatable and
  agent-driveable?

## Findings

### The emulation tier, honestly assessed

**Headline: no emulator exercises ESP-NOW in 2026. The radio is the hard
boundary.** Each candidate stops short of it in a different place:

#### Wokwi (simulator + `wokwi-cli` CI product)

- **Chip coverage.** Wokwi simulates the ESP32, ESP32-C3, -S2, -S3, -C5
  (alpha), -C6, -C61, -H2, -S31 (alpha) and -P4 (beta) [S1100]. For the
  ESP32-S3 specifically: GPIO (with interrupts), SPI, ADC, LEDC and USB-CDC
  are simulated; **RMT is partial, transmit-only — explicitly positioned for
  driving WS2812 strips**; I2S and BLE are not implemented [S1100]. So a
  mesh node's *LED output path* (RMT→WS2812) is simulatable, but not the
  I2S/LCD parallel output path RA-16 favors for high channel counts.
- **WiFi.** Wokwi simulates "a complete network stack from the 802.11 MAC
  layer" up through DNS/HTTP/MQTT, via a virtual open AP ("Wokwi-GUEST",
  channel 6) and a cloud or local IoT gateway carrying TCP and UDP (no ICMP)
  [S1101]. This is *infrastructure* WiFi: STA associate → DHCP → sockets. It
  is enough to exercise DDP-over-UDP receiver code in simulation [S1101].
- **ESP-NOW: not supported.** The feature request ("ESP-NOW support — direct
  communication between two ESP chips") has been open since 2022-11-11,
  status "open for vote", with a 2025 duplicate closed against it; no
  implementation as of 2026-07 [S1113]. Multi-MCU-in-one-project simulation
  is bundled into the same unimplemented request [S1113]. **Wokwi therefore
  cannot test pewpew's mesh tier state-frame path at all.**
- **Speed honesty.** Wokwi caps the simulated CPU clock (default ≈8 MHz
  equivalent, configurable via `cpuFrequency`) "to achieve a higher
  simulation speed" [S1100] — i.e., it is not cycle-accurate real-time; timing
  measurements taken inside Wokwi do not transfer to hardware.
- **CI product.** `wokwi-cli` runs the same engine headlessly: firmware is
  uploaded, simulated in Wokwi's cloud, serial output streamed back;
  scenario YAML files can wait on serial text, set controls, and fail on
  timeout (`--timeout` ms); GitHub Actions (`wokwi/wokwi-ci-action`) and
  GitLab CI are documented, auth via `WOKWI_CLI_TOKEN`; experimental MCP
  server support exists for AI-agent-driven simulation [S1102][S1104]. CI
  minutes are plan-gated: Free 50 min/mo, Hobby/Hobby+ 200, Pro
  ($20/seat/mo) 2000 CI min/mo [S1102][S1103].
- **License / maintenance.** The CLI is MIT and active (v0.26.1 2026-02-23,
  pushed 2026-06) [S1104], but the ESP32 simulation engine itself has no
  public source repository (only the older AVR8js engine is open source
  [S1114]) and execution is cloud-hosted — the engine is a proprietary SaaS
  dependency [S1102][S1104].
- **Form-factor applicability:** dev-time only; useful for receiver-tier
  (DDP/WiFi) firmware logic and RMT-path smoke tests, useless for mesh radio.

#### QEMU-for-ESP32 (Espressif fork, shipped with ESP-IDF)

- **Now a first-class IDF tool**: `idf.py qemu monitor` / `idf.py qemu gdb`
  run and debug an app without hardware; Espressif ships pre-built QEMU
  binaries for Linux/macOS/Windows [S1105].
- **Chip coverage: ESP32, ESP32-C3, ESP32-S3** — S3 works, including
  dual-core-relevant peripherals: GDMA, HMAC, digital signature, SysTimer,
  plus the common set (UART, interrupt matrix, SPI flash, eFuse, RNG,
  AES/SHA/RSA, timer groups, TWAI, **Ethernet**, RGB framebuffer) [S1106].
- **Radio: none.** "Wi-Fi" is explicitly listed as not emulated on all three
  chips; the stated workaround is "the Ethernet controller can be used for
  networking instead" [S1106]. Also **not** emulated: Bluetooth, USB, **RMT**,
  GP-SPI, I2C, I2S, ULP, GPIO matrix/IOMUX [S1106]. So QEMU can run pewpew's
  render/codec/gossip *logic* on a virtual S3 and even push network traffic
  over emulated Ethernet, but neither the LED output path nor any radio path
  exists.
- **Support posture:** "Espressif does not provide support for QEMU. We
  appreciate issue reports but keep in mind that our response may be
  delayed." [S1106]
- **License / maintenance.** GPL-2.0 (QEMU base); active — release
  esp-develop-9.2.2 tagged 2026-04-17, pushed 2026-06 [S1107].
- **Community WiFi emulation exists but is dead**: emb-team's esp-idf-qemu
  fork emulated WiFi STA/softAP + BLE over redirected Ethernet, but it is
  pinned to IDF v3.2.2 and has had no commits since 2020-06-11 — a proof of
  concept, not a path [S1108].

#### Renode (Antmicro)

- **The multi-node radio simulator that doesn't speak ESP32.** Renode's
  wireless story is real: a shared-medium abstraction (e.g. `BLEMedium`)
  connects multiple emulated machines' radios, with packet-interception
  hooks in Python; the canonical demo is two nRF52840s running Zephyr
  exchanging BLE heart-rate data, and multi-node 802.15.4 simulation is
  shipped (`scripts/multi-node/`) [S1109]. In 2025 Antmicro extended this to
  SiLabs Series 2 multi-protocol radios for "complex networks of low-power
  IoT devices" (BLE/Zigbee/Thread/Matter) [S1112].
- **ESP32 status: effectively absent.** No ESP32/Espressif board appears in
  Renode's supported-boards list; the only Xtensa entry is the generic
  `xtensa-sample-controller` [S1110]. ESP32 improvements landed once via a
  community contribution (v1.14 era) but never became a supported platform
  [S1110][NEEDS-VERIFICATION on the exact contributed scope]. Simulating an
  S3 + its WiFi MAC + ESP-NOW in Renode would mean writing the platform and
  the radio model — months of work, not configuration.
- **Where Renode *does* fit pewpew:** the wearable/bridge tier. nRF52840 is
  Renode's best-supported wireless target [S1109], so RA-18's
  BLE-observer-mode bridge logic could in principle run under Renode's
  BLEMedium with scripted packet loss — worth one prototype-day, not more,
  since CircuitPython-under-Renode is itself unproven
  [NEEDS-VERIFICATION].
- **License / maintenance.** MIT (copyright Antmicro) [S1111]; very active —
  v1.16.1 released 2026-02-16, pushed 2026-07-09 [S1111].

#### Conclusion: sim-above / HIL-below

The boundary is crisp [S1100][S1106][S1113]:

| Layer | Best executable environment |
|---|---|
| Codec, gossip merge, PCO math, render core | **Pure Python/C on host** (fastest, deterministic — RA-11's existing story, plus property tests below) |
| IDF app logic, boot, NVS, OTA state machines, task structure | **QEMU-S3** (`idf.py qemu`), Ethernet in place of WiFi [S1105][S1106] |
| WiFi-STA + UDP/DDP receiver behavior | **Wokwi** (MAC-level STA + UDP gateway) [S1101] |
| RMT→WS2812 waveform sanity (logic, not timing) | **Wokwi** (RMT TX partial) [S1100] |
| ESP-NOW, coexistence, real timing, dither-on-LEDs, power | **Hardware only** — the bench below |

### ESP-IDF's own test machinery: pytest-embedded

This is the highest-leverage adoption in the whole doc — Espressif tests
ESP-IDF itself with it, and it composes with QEMU, Wokwi, and real serial
DUTs behind one API.

- **The plugin family.** `pytest-embedded` is "a pytest plugin that has
  multiple services available for various functionalities. Designed for
  embedded testing", with optional packages activated by
  `--embedded-services`: `-serial` (serial port), `-esp` (esptool
  target/port auto-detection), `-idf` (IDF app detection + flashing),
  `-qemu` (run under the QEMU fork), `-wokwi` (run under Wokwi), plus
  `-arduino` and `-nuttx` [S1115]. The same test body —
  `dut.expect(pattern)` / `dut.expect_exact()` on serial output — runs
  against a simulator or a devkit by swapping services [S1115]. MIT
  (packages individually licensed; examples CC0), active: v2.8.1 current on
  PyPI, pushed 2026-06-30 [S1116].
- **How Espressif itself runs it.** ESP-IDF's CI uses pytest-embedded
  (services `esp,idf`) + `pytest-rerunfailures` + pytest-ignore-test-results;
  test apps are standalone IDF projects, built centrally against all
  targets/sdkconfig variants, with binaries fetched by target-test jobs
  [S1117]. Tests are routed to hardware by markers: a *target* marker
  (chip) and an *env* marker that "should be assigned to a CI runner with
  the corresponding tag" — i.e., labeled self-hosted runners with specific
  fixtures attached [S1117].
- **Multi-DUT is first-class** — directly relevant to mesh tests:
  parameterize `count` (e.g. `[2]`) and per-DUT targets `'esp32|esp32s2'`;
  the `dut` fixture becomes a list (`dut[0].expect(...)`,
  `dut[1].expect(...)`); different apps per DUT via `app_path` for
  master/slave scenarios [S1117]. This is exactly the shape of a
  "sender fleet + sniffer" ESP-NOW test.
- **Flake discipline, as practiced by Espressif:** known-flaky tests carry
  `@pytest.mark.flaky(reruns=3, reruns_delay=5)` (pytest-rerunfailures);
  known failures `xfail`; tests without available runners
  `temp_skip_ci` (skip in CI, still run locally) [S1117]. That is a
  ready-made quarantine vocabulary; `pytest-rerunfailures` itself is
  MPL-2.0, v16.4, pushed 2026-07 [S1124].
- **Unity on-target.** Component tests live in `test/` subdirs as C files
  using Unity's `TEST_CASE(name, "[tag]")`; a central unit-test app exposes
  an interactive serial menu; `TEST_CASE_MULTIPLE_DEVICES` coordinates up to
  five DUTs over UART signals (`unity_wait_for_signal`/`unity_send_signal`)
  — built for exactly the two-board protocol tests pewpew needs (e.g. §12
  item 19's broadcast-RX-while-STA check); `TEST_CASE_MULTIPLE_STAGES`
  handles reset-spanning tests (deep sleep, reboot loops) [S1118]. The
  pytest layer drives the menu automatically in CI [S1118][S1117].
- **Applicability:** all pewpew C-firmware tiers (receiver, mesh node,
  gateway dongle). CircuitPython wearables are outside pytest-embedded-idf's
  scope but the `-serial` service can still `expect()` on their REPL output
  [S1115] (inference).

### CI with attached hardware

- **Self-hosted runners are the substrate.** GitHub's runner app runs on
  any machine (physical/VM/container), polls GitHub over HTTPS, and gives
  workflows direct access to locally attached USB hardware; you route jobs
  with `runs-on:` labels [S1120]. Job time limits are the reason soak tests
  fit: GitHub-hosted jobs cap at 6 h, but **self-hosted jobs may run up to
  5 days**, and one workflow run up to 35 days [S1123].
- **Security is the one hard rule:** GitHub recommends self-hosted runners
  only for private repositories, because PRs from forks of public repos can
  execute arbitrary code on the runner [S1120]. Ferrous Systems' HIL setup
  (nRF52840-DK on a Pi 4 runner) solved this with a two-repo pattern — a
  public repo proxies into a private repo that owns the runner — plus
  merge-queue approval before anything touches hardware [S1121].
- **Board-farm practice** (The Good Penguin, 2023): exclusive-use
  arbitration of boards per runner (`bfmc use <board> --force`), USB relays
  for power (`usbrelay <id> 2 off/on` around every flash), SD-mux to hand
  storage between host and target, pytest+pexpect on serial consoles, and
  built images/artifacts through `actions/upload-artifact` [S1122]. The
  recurring lesson across write-ups: devices flashed many times a day end up
  in undefined states, so **power-cycle to a known state before every test
  run** via controllable power (relay, smart PSU, or per-port USB hub
  switching) [S1122][S1121].
- **labgrid — the established open-source lab-bench framework.** Pengutronix's
  labgrid (since 2016, LGPL-2.1, v26.0 released 2026-06-22, pushed
  2026-07-08) abstracts "the hardware control layer": a
  coordinator/exporter/client infrastructure exports boards across the
  network, drivers cover power switches, serial consoles, SSH, digital
  outputs, SD/USB multiplexers, audio/video/measurement devices, and a
  pytest plugin binds it all to tests [S1119]. It is Linux-SBC-flavored
  (bootloader/rootfs workflows) rather than MCU-flavored, but its
  place-and-resource model is the reference design for "one YAML describes
  the bench, tests acquire resources by name" [S1119].
- **Artifact-capture norms.** Serial logs are table stakes (pytest-embedded
  writes per-DUT logs automatically [S1115]); board-farm setups push
  images/logs through the CI artifact store [S1122]; retention/storage is
  plan-limited (500 MB on Free) so waveform/pcap captures need either
  trimming or an external store [S1123]. No widely-adopted standard exists
  for waveform/pcap artifacts — a per-project convention, not an ecosystem
  one [S1122] (absence noted across surveyed sources).

### Instrument automation — making §12's benches scriptable

Everything below is drivable from one Python process, which is the point:
each §12 bench becomes a pytest test, not a lab afternoon.

#### Logic analyzers: sigrok vs Saleae

- **sigrok/sigrok-cli** (GPL-3.0 stack) is fully headless: `sigrok-cli
  --driver fx2lafw --time 3s`, protocol decoders stack via `-P`, output as
  binary/CSV/sigrok-session files — designed for "scripts, CI/CD pipelines,
  and remote/embedded systems" [S1125]. **A WS281x decoder ships in mainline
  libsigrokdecode** (`decoders/rgb_led_ws281x`) — LED frames can be decoded
  to RGB values in CI without custom code [S1126]. libsigrokdecode's last
  push is 2024-10 — slow-moving but the decoder set is stable [S1126].
- **fx2lafw-class hardware** ($10–25 Cypress FX2 "24 MHz 8-channel" clones)
  runs open-source firmware (GPLv2+), 8 channels at up to 24 MS/s [S1127].
  24 MS/s is 30 samples per WS2812 bit (800 kHz), comfortably enough for
  protocol decode and Push-skew timestamping across 8 nodes' data lines
  [S1127][S1126]. It has no analog channels and limited depth (streaming
  over USB2), so it cannot do the photometric benches.
- **Saleae Logic 8** (~mid-hundreds USD; price not published on the product
  page [NEEDS-VERIFICATION]) adds what fx2lafw lacks: 8 digital channels at
  100 MS/s **plus analog recording at 10 MS/s / 10-bit** on the same probes
  [S1130]. Its **Logic 2 Automation API is official**: a gRPC socket wrapped
  by a Python package (`logic2-automation`, Apache-2.0) that starts
  captures, adds analyzers, and exports data; the Logic 2 desktop app must
  be running to serve the socket, with a documented headless-Linux mode
  [S1128][S1129]. The API package is maintained (pushed 2026-05) though
  release-quiet (v1.0.2, 2022) [S1129].
- **Bench implication:** the analog channels make one Saleae both the
  protocol analyzer *and* the photodiode digitizer (10 MS/s dwarfs the
  ~kHz–100 kHz needs of flicker measurement) — collapsing §12 items 3, 5,
  11, 16, 17 onto one instrument [S1130][S1137].

#### Monitor-mode WiFi sniffing for ESP-NOW

- **ESP-NOW rides on vendor-specific 802.11 action frames** [S1054], so any
  monitor-mode capture on the right channel sees the mesh's entire state
  traffic. Two independent capture paths:
  1. **Linux USB adapter in monitor mode.** Mainlined chipsets are the ones
     to buy: Atheros AR9271 (`ath9k_htc`, mainline since kernel 3.2,
     2.4 GHz-only — sufficient for ESP-NOW) and MediaTek MT7612U (`mt76x2u`,
     mainline since 4.19, dual-band) are the community-reference
     recommendations; morrownr/USB-WiFi is the widely-cited compatibility
     list (4.4k stars, pushed 2026-07) [S1135]. tcpdump/Wireshark or scapy
     (`sniff(monitor=True)`, `Dot11` dissection, `wrpcap` for CI artifacts,
     BPF filters at OS level) complete the pipeline [S1136].
  2. **A spare ESP32 as sniffer.** `esp_wifi_set_promiscuous()` +
     `esp_wifi_set_promiscuous_filter()` deliver management frames (action
     frames included) to a callback with `wifi_pkt_rx_ctrl_t` metadata
     (RSSI etc.); stream them up USB serial into a pcap [S1134]. This gives
     per-frame RSSI *as an ESP32 radio sees it* — closer to what fleet
     nodes experience than a Linux adapter — but costs one S3 and custom
     firmware.
- §12 item 15's per-sender PDR counting is precisely a scapy groupby over
  such a capture: count sender MACs per second vs expected 10 Hz [S1136]
  (design inference).

#### Power: Nordic PPK2 as profiler and source-meter

- Official specs: 200 nA–1 A measurement range, resolution to 100 nA,
  **100 kS/s** sampling; in source-meter (SMU) mode it *supplies* 0.8–5 V at
  up to 1 A to the DUT (two USB cables needed for the full 1 A); ampere-meter
  mode inserts in series with an external supply [S1131]. That covers both
  wearable sleep-current verification (§12 item 20's ~0.2 mA claim) and
  powering a node while profiling it.
- **Automation:** Nordic's own UI is the nRF Connect Power Profiler app
  [S1131], but the de-facto automation path is `ppk2-api-python` (IRNAS;
  GPL-2.0 [reuse note: keep it an external process/import boundary], v0.9.x,
  pushed 2026-05, 239 stars): `use_source_meter()`, `set_source_voltage()`,
  `start_measuring()`, `get_samples()`, with a multiprocessing variant that
  buffers the 100 kS/s stream [S1132]. Unofficial but widely used; the
  serial protocol it speaks is undocumented by Nordic
  [S1132][NEEDS-VERIFICATION on long-term protocol stability].

#### Remote power-cycling: uhubctl and per-port USB switching

- `uhubctl` (GPL-2.0, v2.6.0 2024-08, repo pushed 2026-06) switches VBUS
  per-port on hubs that genuinely implement USB per-port power switching
  [S1133]. The hard-won caveat is that **most hubs lie**: many advertise
  per-port switching but gang ports together or never cut VBUS; the README
  maintains the verified-hub list (2026 recommendations include Rosonway
  RSH-A13 13-port and RSH-A37S 7-port, Inateck HB2025A) [S1133].
- This is the bench's reset button: every board-farm writeup converges on
  "power-cycle to known state before each run" [S1122][S1121], and per-port
  hub switching does it for N devkits with one hub and zero relay wiring
  [S1133]. USB smart plugs remain an option for non-USB-powered gear (PSU,
  LED supplies) but per-port hubs cover the devkit fleet.

#### Photodiode → digitizer for flicker/dither measurement

- **Established low-cost design:** an integrated
  photodiode + transimpedance-amplifier chip — the ams **TSL257**
  light-to-voltage converter is the standard pick — pointed at the LED,
  its analog output captured by a scope or digitizer; metrics are percent
  flicker ((Lmax−Lmin)/(Lmax+Lmin)) and flicker index per IEEE 1789-2015,
  which also supplies the risk thresholds (~8 % at 100 Hz) [S1137]. Lab
  instruments sample light at up to 200 kHz for this purpose [S1137] —
  within reach of a Saleae analog channel (10 MS/s) [S1130] or even a
  100 kS/s MCU ADC.
- For pewpew's §12 items 5 and 18 (dither effective-bits vs refresh rate;
  16-bit pipeline verification), the same rig applies: drive a known slow
  ramp, capture luminance vs time, FFT/step-height analysis in NumPy. No
  published LED-strip-dither measurement rig was found (searched
  2026-07-09/10) — the *components* are established, the assembly is ours
  (open lane, same conclusion as RA-11's golden-frame gap).

### Property-based testing and fuzzing above the radio line

Everything that runs in pure Python (the codec, gossip merge, PCO model —
the "sim-above" half of the boundary) should be property-tested, not
example-tested:

- **Hypothesis** (MPL-2.0, v6.156.4, pushed 2026-07 — the standard Python
  property-testing library [S1139]) covers three pewpew-shaped cases:
  1. **The 11-byte codec:** the classic round-trip property —
     `decode(encode(state)) == state` over generated states, plus
     `encode` output length always 11 and decode-of-random-bytes never
     raises unhandled exceptions. Plain `@given` [S1138][S1139].
  2. **Gossip merge (CRDT laws):** associativity, commutativity, and
     idempotence of the merge function are single-line Hypothesis
     properties over generated state triples — these algebraic laws are
     exactly what property testing does best, and together they *prove*
     order-independence of gossip convergence at the model level (the laws
     themselves are standard CRDT requirements; the test method is
     [S1138][S1139]).
  3. **Protocol state machines:** Hypothesis's `RuleBasedStateMachine`
     generates whole interaction *sequences* — `@rule` methods chained,
     `Bundle`s carrying values between steps, `@invariant` checked after
     every step, and failing sequences shrunk to a minimal reproducible
     program [S1138]. Model N nodes as machine state, rules =
     deliver/drop/duplicate/reorder a broadcast, join/leave a node,
     advance time; invariants = epoch monotonicity, eventual-agreement
     bounds. PCO convergence is better checked as a *statistical* property
     (spread decreases over M periods across seeds) in plain pytest, with
     Hypothesis generating topologies/loss patterns (design inference from
     [S1138]).
- **Fuzzing the embedded C parser on the host.** The mesh node's frame
  parser is C; compile it for the host and fuzz there:
  - **AFL++**: active and current (v5.02c 2026-06-29); **relicensed to
    AGPL-3.0 at v5.00c (2026-06-03)** — "AFL++ is now an AGPL 3.0 project"
    — irrelevant for fuzzing *our* code (we run the tool, don't link it),
    but worth recording [S1141].
  - **libFuzzer** (`-fsanitize=fuzzer`, in-process coverage-guided) is in
    maintenance-only mode: "The original authors of libFuzzer have stopped
    active work on it and switched to... Centipede. LibFuzzer is still
    fully supported in that important bugs will get fixed" [S1140]. Fine
    for a small parser harness; don't build infrastructure around it.
  - **Espressif's own pattern is the template:** esp-protocols' mDNS
    component ships a host-side harness — "builds the mDNS component as a
    Linux host binary with stubs for ESP-IDF networking", with two modes:
    Unity/CMock unit tests under ASan/UBSan, and an "AFL++ harness that
    feeds random packets into the receive path"
    [S1142:components/mdns/tests/host_unit_test/README.md]. pewpew's
    11-byte parser is ~100× smaller than an mDNS parser; the same
    stub-the-IDF, fuzz-the-parse-function recipe applies directly [S1142].
  - Cross-check bonus: fuzz the C parser and the Python codec against each
    other (differential testing) — any input where `parse_c(x)` ≠
    `parse_py(x)` is a bug in one of them (design inference).

### Long-soak orchestration

Published practice is thin here; what is citable:

- **Soak as background CI job is feasible on self-hosted runners only**:
  job limit 5 days self-hosted vs 6 h GitHub-hosted; a workflow run may
  span 35 days [S1123]. A 2-week soak (§12 item 17) therefore needs either
  chained 5-day jobs (each re-queues the next, state on disk) or a runner-
  external daemon that CI merely *queries* — the latter is simpler and
  keeps the soak alive across CI outages (design inference from [S1123]).
- **Scheduled health snapshots**: `schedule:` cron (min interval 5 min;
  runs may be delayed or dropped under load; default branch only;
  auto-disabled after 60 days of repo inactivity on public repos) +
  `workflow_dispatch` for manual triage runs [S1143]. A soak, then, is:
  daemon on the bench host appends periodic health records (per-node PDR,
  heap, RSSI, fps counters, PPK2 current stats) to newline-JSON; a
  scheduled workflow reads the latest snapshot and fails loudly on
  regression — turning a multi-day soak into many small, retryable CI
  checks (design inference from [S1143][S1123]).
- **Triage artifacts**: capture on *state change*, not continuously —
  ring-buffer serial logs per node (pytest-embedded already writes per-DUT
  logs [S1115]), start a sniffer pcap [S1136] and a logic capture [S1125]
  only when a health check trips, then upload the window as a CI artifact
  (mind plan storage caps [S1123]). Norms here are per-project; no
  ecosystem standard was found (searched 2026-07-09/10).

### Candidate bench BOM + software stack

Two build points. Street prices are 2026-07 approximations, not quotes —
line items marked ✱ were not price-verified from an official source
[NEEDS-VERIFICATION on ✱ prices only; capabilities are cited].

**~$200 core bench (every §12 mesh item becomes runnable):**

| Item | Qty | ~Cost | Role | Automation path |
|---|---|---|---|---|
| ESP32-S3 devkits (e.g. DevKitC-1) | 6 | ~$90✱ | mesh senders / sniffer / gateway DUTs | pytest-embedded-idf flash+expect [S1115][S1117] |
| uhubctl-verified powered hub (e.g. Rosonway RSH-A37S 7-port) | 1 | ~$35✱ | per-port power-cycle to known state | uhubctl CLI from Python [S1133] |
| fx2lafw-class 8-ch logic analyzer | 1 | ~$15✱ | WS2812 decode, Push-skew, GPIO-edge sync-spread | sigrok-cli + rgb_led_ws281x decoder [S1125][S1126][S1127] |
| AR9271 USB WiFi adapter (e.g. Alfa AWUS036NHA) | 1 | ~$30✱ | monitor-mode ESP-NOW/action-frame capture, 2.4 GHz | tcpdump/scapy `sniff(monitor=True)` → pcap artifacts [S1135][S1136] |
| TSL257 light-to-voltage sensor + jig | 2 | ~$10✱ | flicker/dither/latency photometry | analog capture (below) [S1137] |
| Pi 5 or N100 box as bench host + runner | (existing) | — | self-hosted runner, all instruments attach here | GH runner labels; private repo or two-repo proxy [S1120][S1121] |

At this tier the photodiode digitizer is an MCU ADC (a spare Pico/S3
sampling the TSL257 at ~100 kS/s) — adequate for percent-flicker and
dither-step analysis per the 200 kHz lab bar [S1137], but it's the
weakest, most-custom link.

**~$500 build adds:**

| Item | ~Cost | What it buys |
|---|---|---|
| Saleae Logic 8 | ~$400✱ | replaces fx2lafw AND the ADC hack: 8 digital ch @100 MS/s + analog @10 MS/s/10-bit, official Python (gRPC) automation, protocol analyzers in-app [S1128][S1129][S1130]. One instrument for §12 items 3, 5, 11, 16, 17. |
| Nordic PPK2 | ~$100✱ | 200 nA–1 A @100 kS/s power profiling AND 0.8–5 V/1 A source-meter for wearable-tier benches (§12 item 20); `ppk2-api-python` automation [S1131][S1132] |

**Software stack (one Python harness, all free):** pytest +
pytest-embedded (`esp,idf` services; `-qemu`/`-wokwi` for the sim tiers)
[S1115][S1117] + pytest-rerunfailures for quarantine [S1124] + uhubctl
(subprocess) [S1133] + sigrok-cli or logic2-automation [S1125][S1128] +
scapy [S1136] + ppk2-api [S1132] + Hypothesis for the pure-Python layers
[S1138]. Runner: GitHub Actions self-hosted on the bench host, labeled
(e.g. `bench-mesh`), private repo or proxy-repo pattern [S1120][S1121];
soak daemon outside CI with scheduled check-in workflows [S1143].

What the $200 build cannot do: per-frame analog photometry at high sample
rates (MCU-ADC rig is DIY), multi-channel analog, and calibrated power
measurement (no PPK2 — wearable current claims stay unverified). What
neither build does: RF-shielded repeatability (open-air 2.4 GHz PDR
numbers will vary run-to-run — treat item-15-style results as
distributions, not point values; flake discipline per [S1117][S1124]).

## Verdicts

- **Wokwi + wokwi-cli**: ascendant as a CI product (MCP agent hooks, active
  CLI, plan-gated minutes) [S1102][S1104] — but a proprietary cloud engine
  [S1114], no ESP-NOW (open request since 2022 [S1113]), and non-real-time
  clock [S1100]. Use for receiver-tier WiFi/UDP logic; never for timing or
  mesh.
- **QEMU-for-ESP32**: stable/ascendant — first-class `idf.py qemu`, S3
  supported, active releases [S1105][S1107]; radio permanently out of scope
  (Ethernet substitute) [S1106]. Use for firmware logic tests in plain CI.
- **Radio emulation for ESP32 (any tool)**: nonexistent — Wokwi lacks
  ESP-NOW [S1113], QEMU lacks WiFi [S1106], Renode lacks the platform
  [S1110]; the one community attempt died in 2020 [S1108]. HIL is not
  optional for the mesh tier.
- **Renode**: ascendant generally (active, MIT, growing radio-medium
  ecosystem [S1111][S1112]) but not for ESP32 [S1110]; keep on the shelf
  for nRF52840 bridge-logic simulation [S1109].
- **pytest-embedded**: ascendant — Espressif's own CI framework, MIT,
  active, multi-DUT and sim-backends behind one API [S1115][S1116][S1117].
  The backbone of pewpew's HIL harness.
- **Unity on-target + multi-device tests**: stable — mature IDF machinery,
  the native shape for 2-board radio checks [S1118].
- **labgrid**: stable — 10-year-old, actively maintained, LGPL-2.1; adopt
  its *resource model*, adopt the tool itself only if the bench outgrows
  one host [S1119].
- **Self-hosted-runner HIL**: stable practice with known patterns (labels,
  private/proxy repos, power-cycle-before-test) [S1120][S1121][S1122].
- **sigrok stack**: stable — slow-moving but complete for our protocols
  (WS281x decoder in mainline) [S1125][S1126]; fx2lafw hardware is the
  eternal $15 workhorse [S1127].
- **Saleae Logic 2 automation**: stable — official, gRPC+Python, maintained
  [S1128][S1129]; the analog channels are the differentiator [S1130].
- **PPK2 + ppk2-api-python**: stable — the default affordable
  power-automation rig; API unofficial but healthy [S1131][S1132].
- **uhubctl**: stable — the standard per-port USB power tool; hub selection
  is the only risk [S1133].
- **Hypothesis**: ascendant/stable — the standard, actively developed;
  stateful testing fits gossip/PCO models exactly [S1138][S1139].
- **AFL++**: ascendant (v5.x, June 2026) with a 2026 license pivot to
  AGPL-3.0 (tool-use unaffected) [S1141]; **libFuzzer**: waning —
  maintenance-only by its own docs [S1140]. Prefer AFL++, per Espressif's
  own harness practice [S1142].

## Code-reading queue

1. **espressif/pytest-embedded** [S1116] — the `-serial`/`-idf` service
   internals: DUT lifecycle, port auto-detection, per-DUT log files,
   multi-DUT `count` fixture plumbing. Answers: what does pewpew's bench
   conftest actually import vs re-implement?
2. **esp-protocols mDNS host harness** [S1142] —
   `components/mdns/tests/host_unit_test/`: the IDF-stubbing CMake tricks
   and the AFL++ receive-path harness. Answers: the exact recipe for
   host-fuzzing pewpew's frame parser.
3. **labgrid** [S1119] — resource/place YAML model and the power-driver
   abstraction. Answers: bench-description schema worth imitating (not
   adopting) for a one-host bench.
4. **wokwi-cli** [S1104] — scenario-file schema and the `expect`/timeout
   loop; the MCP server surface. Answers: whether agent-driven Wokwi runs
   fit the receiver-tier smoke suite, and what a scenario file can and
   cannot assert.
5. **ppk2-api-python** [S1132] — the reverse-engineered serial protocol and
   the multiprocessing sampler. Answers: robustness of unattended multi-day
   PPK2 capture (buffer overruns, reconnect).
6. **sigrok rgb_led_ws281x decoder** [S1126:decoders/rgb_led_ws281x] —
   timing windows it accepts vs WS2812/SK6812 datasheet windows. Answers:
   whether the decoder can arbitrate §12 item 17's marginal-timing
   question or needs a stricter custom decoder.

## Open questions

- **Wokwi RMT fidelity**: RMT is "partial, transmit-only" [S1100] — does it
  model RMT timing well enough to catch a wrong-bit-period bug, or only
  data-level WS2812 emission? Settle with one deliberate-off-timing sketch
  in Wokwi (an afternoon).
- **pytest-embedded-wokwi + private gateway**: can Wokwi CI exercise a
  UDP/DDP stream from a host-side test process (private gateway supports
  local servers [S1101]) — i.e., can a *real* pewpew host engine feed a
  *simulated* receiver? Settle by prototype; nothing in the docs forbids it.
- **QEMU-S3 dual-core + Ethernet throughput**: is emulated performance
  sufficient to run the mesh node's full task structure at 10 Hz epoch
  cadence (no radio, gossip over UDP/Ethernet)? No published QEMU-ESP32
  performance figures found (searched 2026-07-09/10). Settle by benchmark.
- **Renode + CircuitPython on nRF52840**: does CircuitPython boot under
  Renode's nrf52840 platform at all? Would unlock bridge-logic simulation
  [S1109][NEEDS-VERIFICATION]. Settle with a one-day spike.
- **Saleae Logic 8 current price/availability** and whether Logic 2's
  headless-Linux mode runs on an ARM (Pi 5) bench host [S1128]
  [NEEDS-VERIFICATION]. Settle by checking Saleae's download matrix before
  purchase; fallback is an x86 N100 bench host.
- **PPK2 serial-protocol stability** under ppk2-api-python across nRF
  Connect firmware updates [S1132][NEEDS-VERIFICATION]. Settle by pinning
  PPK2 firmware version on the bench.
- **Monitor-mode capture completeness at 1 Mbps broadcast storms**: do
  AR9271-class adapters drop frames under §12 item 15's load? No published
  figure; the two-sniffer trick (Linux adapter + ESP32 promiscuous counter
  [S1134]) cross-checks capture loss. Settle on the bench.
- **Flake-quarantine policy numbers**: Espressif's `flaky(reruns=3,
  reruns_delay=5)` [S1117] is a starting point, but pewpew needs its own
  quarantine ladder (retry → quarantine label → block-merge) — no
  published embedded-specific policy found beyond retry counts; decide in
  ADR when the bench exists.
- **Whether any commercial device farm (2025–2026) is worth renting for
  the 25–50-node scale test**: nothing surveyed offers ESP-NOW-capable
  RF-coherent fleets; appears genuinely unavailable, but this pass did not
  exhaustively survey commercial farms — revisit if the in-house bench
  can't reach 20+ nodes.
