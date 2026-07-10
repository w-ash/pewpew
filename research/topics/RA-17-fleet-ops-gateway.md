# RA-17: Fleet operations & the ESP-NOW↔IP gateway

Last researched: 2026-07-09
Status: draft
S-ID block: S1000–S1049

## Key questions

- Can one ESP32/S3 run ESP-NOW and WiFi STA simultaneously, and what does the
  shared-channel constraint actually cost? What are the documented patterns and
  pitfalls (esp_wifi channel APIs)?
- Is a USB/serial-attached ESP-NOW "coordinator dongle" (Zigbee-style) a better
  gateway than a WiFi-attached one — precedents, latency, simplicity?
- Is a two-radio gateway (one chip ESP-NOW, one chip WiFi/Ethernet, UART
  between) ever justified at this scale?
- Latency budget: host command → gateway → ESP-NOW broadcast — what is
  achievable over USB-CDC vs a WiFi hop?
- Telemetry backhaul: nodes → gateway → host at what rates without two-way
  traffic storms?
- Python host side: serial protocol vs UDP; any established ESP-NOW-gateway
  conventions/libraries worth adopting (ESPHome's ESP-NOW status)?
- OTA at 25–150 nodes: standard esp_ota dual-partition + rollback + optional
  signing; time to flash N nodes serially vs parallel; maintenance-window
  practice; why mesh-gossiped OTA is not worth it here.
- Fleet workflow: versioning, staged rollout, catching the node that missed
  the window via version telemetry.
- Provisioning & identity: MAC-derived IDs, config-vs-firmware separation
  (NVS), zero-touch join with no network infrastructure.

## Findings

### The channel constraint (why the gateway is a design problem at all)

- ESP-NOW and WiFi STA can coexist on one chip — this is a standard IDF
  feature on every WiFi-capable ESP32 variant — "but it should be noted that
  the channel of ESP-NOW must be the same as that of the connected AP"
  [S1000]. Once associated, "the device cannot switch channels after
  connecting to Wi-Fi. It can only transmit and receive data on the current
  Wi-Fi channel" [S1000]. ESPHome's component docs state the same rule from
  the other side: the ESP-NOW channel "Cannot be set when Wi-Fi is used, as
  ESP-NOW will use the same channel as the Wi-Fi network" [S1008].
- Consequence for pewpew: a WiFi-attached gateway does not merely constrain
  itself — it constrains the **entire mesh**. Every light node must sit on
  whatever channel the venue's AP happens to use, because ESP-NOW peers only
  hear each other on a shared channel (senders in the documented single-chip
  gateway pattern scan for the gateway's AP channel and apply it with
  `esp_wifi_set_channel()`) [S1012][S1000]. The mesh's RF environment becomes
  hostage to the venue router — including channel changes made by an
  auto-channel-selecting AP after deployment, which strands the fleet
  [S1000] (consequence is inference; the no-switch-after-connect rule is
  cited).
- Coexistence pitfalls are real and documented: ESP-NOW alongside WiFi STA
  was broken before IDF 5.0 (Espressif staff: "this issue is fixed in IDF 5.0
  and later version"; the 4.x workaround was to init ESP-NOW before
  connecting) [S1002]. In the same thread an Espressif engineer claimed a
  STA-connected node "will only receive the broadcast packet whose bssid is
  equal to the associated AP bssid" — disputed by the reporter in-thread, and
  alarming if true for a broadcast-receiving gateway; needs a bench test on
  current IDF [S1002][NEEDS-VERIFICATION].
- Power save interacts with receive reliability: the default WiFi power-save
  mode is Modem-sleep `WIFI_PS_MIN_MODEM`, and "after entering Modem-sleep
  mode, devices cannot receive ESP-NOW data" between wake windows; a
  coexisting gateway either runs `WIFI_PS_NONE` (which "minimizes the delay
  in receiving Wi-Fi data in real time" at higher power) or tunes the
  connectionless-module wake interval (`esp_wifi_set_connectionless_interval`)
  [S1000][S1004]. For a mains-powered gateway node, `WIFI_PS_NONE` is the
  obvious setting; the sleep hazard mainly matters if a light node is ever
  asked to double as gateway.

### Gateway pattern A — single chip, WiFi STA + ESP-NOW (the tutorial-standard pattern)

- The pattern is well-trodden: one ESP32 in `WIFI_AP_STA`/STA mode receives
  ESP-NOW frames and simultaneously serves IP traffic; "The ESP32 sender
  boards must use the same Wi-Fi channel of the receiver board", with senders
  discovering the channel by scanning for the gateway's SSID and pinning it
  via `esp_wifi_set_channel()` [S1012]. Ordering pitfall: connect WiFi first,
  then set up ESP-NOW peers — the channel is only final after association
  [S1012][S1002].
- Pros: one board, no serial protocol, gateway can be physically remote from
  the host (anywhere on the LAN), and host↔gateway transport is ordinary
  UDP/TCP which pewpew's Python control plane already speaks (the host
  control plane is WebSocket/JSON-native, §5 of the architecture).
- Cons: (1) the whole-mesh channel hostage problem above [S1000][S1012];
  (2) the WiFi hop inherits AP scheduling/retry jitter — with power save off
  the added latency is small but unbounded under contention, whereas
  Espressif's own lab numbers (75–85 Mbit/s UDP in a shielded box) say
  nothing about a crowded venue channel [S1004]; (3) the gateway is now
  competing for airtime on the same channel it must keep clear for ~10 Hz
  mesh broadcasts — WiFi traffic and ESP-NOW traffic share one radio and one
  channel [S1000].

### Gateway pattern B — serial-attached ESP-NOW dongle (Zigbee-coordinator style)

- Precedent 1, first-party: the espressif/esp-now component's get-started
  example is exactly this device — one board takes bytes from the serial
  port and broadcasts them to all nodes via ESP-NOW; receiving boards emit
  received payloads back out their serial ports [S1001]. Espressif ships the
  pattern as the introductory example of its ESP-NOW application component.
- Precedent 2, ecosystem-scale: this is the standard Zigbee topology. Home
  Assistant's ZHA runs the network through "a hardware radio adapter
  (typically a USB dongle) that plugs directly into the same computer",
  speaking a serial protocol (EZSP, Z-Stack ZNP, deCONZ, XBee) to the host
  [S1015]. The host owns all logic; the dongle owns the radio and the
  timing-critical MAC work. Ten-plus years of smart-home practice validate
  the division of labor.
- On ESP32-S3 the dongle needs no bridge chip: the built-in USB Serial/JTAG
  controller enumerates as CDC. Its documented behavior differs from an
  external UART bridge — the host waits for the device to ingest bytes
  (flow-controlled) rather than fire-and-forget, and if no terminal drains
  the TX buffer the device does "a one-time wait of 50 ms" then discards;
  the controller dies in light/deep sleep and disappears from the host if
  firmware reconfigures its pins [S1009]. None of these bite a mains-powered,
  never-sleeping dongle, but the 50 ms stall-on-disconnected-host means
  gateway firmware must never block on serial writes in the radio path
  [S1009].
- Latency: no published round-trip measurement for S3 USB-CDC was found from
  an established source this pass (open question). Structurally the path is
  host-USB (full-speed, ms-scale polling) → firmware → `esp_now_send()`, with
  no AP, no association, no DTIM, no contention with the mesh's channel from
  the IP side — every latency contributor is local and fixed, unlike the
  WiFi hop whose jitter depends on third-party airtime [S1004][S1009]
  (comparison is inference from the cited mechanisms).
- Pros: mesh channel is freed — the dongle never associates to an AP, so
  `esp_wifi_set_channel()` can put the fleet on whatever channel a site
  survey says is cleanest [S1000] (the no-AP case is exactly the case where
  the channel is freely settable). Failure domain is trivially observable
  (USB device present or not); host-side it is a serial port, the same
  operational shape as ZHA's coordinators [S1015]. The get-started example
  is Apache-2.0 and current (last push 2026-02-04) [S1001].
- Cons: gateway must be within a USB cable of the host machine (placement
  constraint — the host's radio position matters now); one more physical
  artifact to not lose; serial framing protocol is pewpew's to define (the
  esp-now example's framing is line-oriented demo code, not a protocol to
  adopt wholesale) [S1001].

### Gateway pattern C — two-radio gateway (ESP-NOW chip + WiFi/Ethernet chip, UART between)

- This is pattern B with the host replaced by a second ESP32: chip 1 does
  ESP-NOW on the mesh's channel, chip 2 does WiFi/Ethernet on the venue's
  channel, UART between them. It buys pattern B's channel freedom plus
  pattern A's placement freedom.
- No first-party or widely-adopted ESP-NOW-specific implementation of this
  was found this pass; the components are all standard (the esp-now serial
  example on chip 1 [S1001], any UART-to-TCP firmware on chip 2), but the
  integration burden — two firmwares, an inter-chip framing protocol, a
  power/enclosure design — is pewpew's alone (absence-of-precedent is a
  search result, not proof of absence).
- Verdict-shaping observation: at 25–50 nodes with an optional host, the
  only scenario demanding pattern C is "host far from mesh AND venue AP
  channel unusable for the mesh." That is a plausible but narrow corner;
  carrying a custom two-board product to cover it pre-emptively is not
  justified. If it arises, a Raspberry-Pi-class relay running the Python
  gateway shim with a USB dongle (pattern B, host-side split) covers it with
  zero new firmware.

### Latency budget: host command → LEDs

- Target framing: mesh state broadcasts run at ~10 Hz, so one inter-frame
  interval is 100 ms; a live parameter edit that reaches the air within
  ~1–2 frame intervals feels immediate in the playground sense (§5 host
  control plane; threshold is a design choice, not a cited fact).
- Pattern B path: host serial write → dongle parse → `esp_now_send()`.
  USB full-speed transactions and the flow-controlled USB Serial/JTAG
  controller put the serial leg in the low-millisecond range [S1009]
  [NEEDS-VERIFICATION — no published RTT figure found; prototype
  measurement required]; ESP-NOW airtime for a ≤250 B frame at the 1 Mbps
  default rate is ~2 ms of air, and RA-13's sources cover measured ESP-NOW
  delivery latency [S800]. Total budget: single-digit milliseconds,
  plausibly ~5 ms, dominated by USB polling — two orders of magnitude
  inside the 100 ms frame interval.
- Pattern A path: host UDP → AP → gateway → `esp_now_send()`. With
  `WIFI_PS_NONE` the added hop is normally a few ms, but the gateway
  inherits AP scheduling and shares its one radio between the IP hop and the
  mesh; under a congested venue channel both legs degrade together
  [S1004][S1000]. Median latency is fine; the tail is the problem.
- Either way the latency question is settled in pewpew's favor at 10 Hz:
  both patterns are far inside budget in the median. The differentiator is
  tail behavior and channel freedom, not median speed.

### Telemetry backhaul without traffic storms

- Downlink (host → mesh) stays broadcast-only: one ESP-NOW broadcast per
  parameter-change or per state tick regardless of fleet size — broadcast is
  unacknowledged and peers are "theoretically unlimited" [S1000][S1008].
  The storm risk is entirely on the uplink.
- Uplink discipline: N nodes must not answer the same trigger in the same
  instant. ESP-NOW broadcasts carry no ACK and CSMA gives no fairness
  guarantee at burst onset [S1008][S800]. Two boring, adequate mitigations
  for 25–150 nodes: (1) unsolicited low-rate beacons — each node emits a
  compact status frame (version, uptime, vitals) every 10–30 s with a
  MAC-derived phase offset so emissions spread across the window;
  (2) polled readback — the gateway unicasts a query when the host actually
  asks. At 150 nodes × one 250 B frame / 10 s, uplink telemetry is ~15
  frames/s — well under the ~10 Hz × N-source state traffic the mesh already
  carries (arithmetic; frame cap cited [S1008]).
- Precedent that rich uplink over ESP-NOW works: the esp-now component ships
  a `wireless_debug` example (log/debug traffic redirected over ESP-NOW to a
  collector) [S1001] — evidence the component authors expect exactly this
  gateway-as-collector topology.

### Python host side: serial vs UDP, and what exists to adopt

- No established Python "ESP-NOW gateway" convention exists to adopt. The
  closest ecosystem motion is ESPHome's: a first-party `espnow` component
  (unicast/broadcast, `auto_add_peer`, broadcast triggers) [S1008] and, as
  of 2025.11, "ESP-NOW now available as transport platform for
  packet_transport component, enabling direct ESP32-to-ESP32 wireless sensor
  data transmission" [S1014]. ESPHome's investment (component in 2025.8,
  transport in 2025.11, ESP-NOW RX moved onto a ~12 µs low-latency event
  path) signals the protocol is ascendant in the home-automation world
  [S1014] — but ESPHome's transport frames sensor/binary-sensor state for
  Home Assistant, not a 10 Hz show-state tree; adopting its wire format
  would buy pewpew nothing it needs and a dependency it doesn't [S1008]
  [S1014] (assessment).
- For pattern B the host side is a serial port — operationally identical to
  how ZHA drives Zigbee radios via pyserial-class transports [S1015].
  A compact length-prefixed binary framing with a version byte and CRC is a
  half-day of work and stays pewpew-owned; the esp-now get-started example
  demonstrates the firmware side [S1001]. For pattern A the host side is a
  UDP or WebSocket client — which pewpew's control plane already has (§5).

### OTA at fleet scale — standard, windowed, boring

- The IDF-native model: at least two OTA app slots plus an otadata partition;
  new firmware is written to the inactive slot and otadata flips the boot
  choice [S1003]. Rollback: with `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE`,
  a new image boots in `ESP_OTA_IMG_PENDING_VERIFY`; the app must call
  `esp_ota_mark_app_valid_cancel_rollback()` after self-test or the
  bootloader reverts on the next reboot [S1003]. A node therefore cannot be
  soft-bricked by a bad-but-bootable image — the fleet-scale property that
  makes maintenance windows low-drama [S1003].
- Signing without ceremony: "the verification of signed OTA updates can be
  performed even without enabling hardware secure boot"
  (`CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT`) — image signature checks on
  OTA ingest, no eFuse burning, no irreversible chip state [S1003]. Optional
  eFuse anti-rollback exists ("the version in the bootable firmware must be
  greater than or equal to the version in the chip", max 16 increments) but
  is aimed at hostile-user products, overkill for an art fleet [S1003].
- Time to flash N nodes: no authoritative per-node wall-time figure was
  found for WiFi OTA from an established source (open question; depends on
  image size, AP quality, flash write speed). The one first-party fleet
  number found is for ESP-NOW OTA: espressif/esp-now's OTA feature claims
  "50 devices can be upgraded in 3 minutes", with fixed-size subpackaging
  and break-point resume [S1001] — which is simultaneously (a) evidence that
  parallel fleet upgrade is a solved problem at pewpew's scale, and (b) the
  strongest argument that if windowed WiFi OTA ever proves too slow, the
  escape hatch is Espressif's maintained Apache-2.0 component, not a custom
  gossip protocol [S1001].
- Why not mesh-gossiped OTA at 25–150 nodes:
  - painlessMesh, the canonical hobby mesh with built-in OTA gossip,
    documents the failure mode: the OTA API "does not allow tracking of the
    OTA update process across the network", nodes reboot "without any chance
    for the gateway to know what is going on", and per-node chunk requests
    "can in some cases create a lot of additional network traffic" [S1006].
    Distribution without observability is exactly wrong for a maintenance
    window whose success criterion is "every node confirmed on version X."
  - ESP-MESH-LITE's supported in-mesh OTA (root downloads then disseminates
    to child nodes) comes with tuning obligations — `CONFIG_OTA_DATA_LEN`
    against RAM, max-node-number, max-tree-level against latency — i.e.,
    mesh OTA is a configuration surface even when a vendor maintains it
    [S1005].
  - The fungibility argument: at ≤150 nodes in one venue during a deliberate
    window, every node is one hop from a maintenance AP or the operator's
    hands. Gossip distribution solves a reach problem pewpew does not have,
    and buys it with the observability problems above [S1006][S1005]
    (synthesis).
- Practical fleet workflow (playbook sketch, §Recommended architecture):
  every image embeds `esp_app_desc_t` — version string (≤32 chars), project
  name, compile date/time, IDF version, ELF SHA-256 — at a fixed offset,
  readable at runtime via `esp_app_get_description()` and "useful for
  identification of images uploaded via Over-the-Air (OTA) updates" [S1013].
  Nodes put the version (or ELF-SHA prefix) in their telemetry beacon; the
  host renders a fleet-version table; a node that missed the window is
  visible within one beacon period and can be retried individually [S1013]
  (workflow is design; mechanism cited).

### Provisioning & identity — zero-touch by construction

- Identity is free: every chip's base MAC is "pre-programmed into the
  ESP32-S3 eFuse in the factory during production", readable via
  `esp_read_mac()`/`esp_efuse_mac_get_default()`; interface MACs derive from
  it [S1011]. A node ID = (a hash of) the base MAC needs zero provisioning
  steps, is stable across reflashes, and is exactly what appears as the
  ESP-NOW source address on the air anyway [S1011][S800].
- Config-vs-firmware separation: NVS is a dedicated flash partition of
  namespaced key-value pairs with power-fail safety ("one should be able to
  power off the device at any point and time and then power it back on") and
  built-in wear levelling [S1010]. Because OTA rewrites only the app slots
  and otadata [S1003], NVS content — friendly name, group assignment, cal
  offsets — survives every firmware update; note the docs do not spell out
  the survives-OTA property in one sentence, it follows from the partition
  model [S1010][S1003][NEEDS-VERIFICATION as a stated guarantee, though it
  is universal practice].
- Zero-touch join: an unencrypted broadcast fleet has no join step at all —
  a freshly flashed node on the right channel hears broadcasts immediately;
  ESPHome models the same posture with `auto_add_peer` and `on_broadcast`
  [S1008]. The entire "provisioning" burden reduces to: (1) flash the
  fleet image, (2) ensure the channel constant matches, (3) optionally write
  a friendly name into NVS. For comparison, the esp-now component's full
  provisioning stack (ECDH + PoP session keys, "16 devices can be configured
  in 5 seconds", first device shares WiFi credentials with the rest) exists
  for the encrypted/WiFi-credentialed case pewpew's tier deliberately avoids
  [S1001] — worth knowing it exists if encryption ever becomes a requirement.
- The one genuinely provisioned datum is the RF channel. Baking it into
  firmware makes channel changes an OTA; storing it in NVS with a
  broadcast "change channel" command makes it runtime-mutable but adds a
  failure mode (a node that misses the command is stranded on the old
  channel). At this scale, firmware-constant channel + OTA-to-change is the
  simpler, self-healing choice (design reasoning; channel mechanics cited
  [S1000]).

### Recommended gateway architecture

- **Primary: pattern B — USB serial dongle on the host.** An ESP32-S3 dev
  board running a thin firmware: length-prefixed frames in over USB-CDC →
  ESP-NOW broadcast out; received mesh frames → USB-CDC in. First-party
  precedent (esp-now get-started, Apache-2.0, active) [S1001]; ecosystem
  precedent (ZHA's serial coordinator model) [S1015]; frees the mesh channel
  from the venue AP [S1000]; single-digit-ms command path with no RF tail
  risk on the IP leg [S1009][S800]. The host is optional in pewpew's tier —
  and so, symmetrically, is its dongle: unplug it and the mesh continues.
- **Fallback: pattern A — single-chip WiFi-STA gateway** for deployments
  where the host cannot be near the mesh: same node firmware, plus WiFi
  association and a UDP/WebSocket leg; accept the venue-AP channel coupling
  and the ordering/power-save pitfalls (`WIFI_PS_NONE`, connect-then-init)
  [S1012][S1002][S1000][S1004]. The documented tutorial pattern plus IDF 5.x
  fixes make this low-risk to implement, just strategically worse.
- Rejected: pattern C (two-radio custom gateway) — no maintained precedent
  found, narrow scenario coverage, and a Pi-plus-dongle relay reproduces it
  from stock parts if ever needed (this doc, pattern C section).

## Verdicts

- **espressif/esp-now component**: stable — first-party, Apache-2.0, last
  push 2026-02-04; ships the exact gateway/OTA/provisioning primitives this
  tier needs; adopt patterns from it, and its OTA if windowed WiFi OTA
  disappoints [S1001].
- **Single-chip STA+ESP-NOW gateway pattern**: stable — documented by
  Espressif FAQ and the standard tutorials, functional since IDF 5.0, but
  strategically penalized by the shared-channel constraint [S1000][S1002]
  [S1012].
- **Serial-dongle gateway pattern**: stable/ascendant — normalized by a
  decade of Zigbee coordinators and Espressif's own introductory example;
  the S3's built-in USB-CDC removes the last hardware friction [S1015]
  [S1001][S1009].
- **ESPHome ESP-NOW support**: ascendant — new first-party component
  (2025.8) plus packet-transport platform (2025.11) with dedicated
  low-latency plumbing; wrong wire format for pewpew but strong evidence of
  platform momentum [S1008][S1014].
- **painlessMesh (incl. its OTA)**: waning — GPL-3.0, low-intensity
  maintenance (last code commit on develop 2025-10-01; repo activity
  2026-06-14), OTA observability gaps acknowledged in its own tracker
  [S1007][S1006]. Do not build around it.
- **ESP-MESH-LITE OTA**: stable — vendor-maintained (Apache-2.0 component,
  last push 2025-09-30) but solves a topology pewpew doesn't have; its
  tuning surface is the cautionary tale, not the offering [S1005].
- **IDF dual-slot OTA + rollback + signed-apps-without-secure-boot**: stable
  — the boring core to standardize on; anti-rollback eFuse machinery is
  overkill here [S1003].

## Code-reading queue

1. **espressif/esp-now `examples/get-started`** (pinned @4432294) — the
   UART↔ESP-NOW bridge loop: framing, retransmission config, send-callback
   handling; steal the structure for the dongle firmware [S1001].
2. **espressif/esp-now `examples/ota` + `src/ota`** — how they hit "50
   devices in 3 minutes": subpackage size, resume bookkeeping, status
   reporting; evaluate as the fallback fleet-OTA path [S1001].
3. **ESPHome `components/espnow`** — production-quality ESP-NOW RX path on
   the new low-latency event loop; peer table handling and broadcast
   triggers; what a maintained integration considers pitfalls worth coding
   around [S1008][S1014].
4. **esp-idf `examples/system/ota/native_ota_example` and
   `advanced_https_ota`** — rollback self-test placement and
   `esp_https_ota` usage for the maintenance-window updater [S1003].
5. **espressif/esp-now `examples/wireless_debug`** — the telemetry-collector
   topology in first-party form [S1001].

## Open questions

- **USB-CDC round-trip latency on ESP32-S3**: no published measurement from
  an established source found; the design assumes low-single-digit ms.
  Settle with a 30-minute bench test (host timestamp → dongle echo →
  host timestamp) on the actual dongle firmware [S1009].
- **The BSSID broadcast-filter claim** [S1002]: an Espressif engineer stated
  a STA-associated node only receives ESP-NOW broadcasts whose BSSID matches
  its AP; disputed in-thread and possibly 4.x-era. If true on IDF 5.x it
  quietly breaks pattern A's receive path. Settle with a two-board test on
  current IDF.
- **Wall-clock time for windowed WiFi OTA of one node and of 50 nodes in
  parallel** (our image size, one maintenance AP): no citable figure found;
  determines whether the esp-now-component OTA fallback is ever needed
  [S1001][S1003]. Settle by measuring during the first fleet prototype.
- **Venue-AP auto-channel behavior** under pattern A: how common is
  post-deployment channel migration on consumer/venue APs, and does the
  gateway re-associate gracefully while the fleet strands? Only matters if
  the fallback pattern is deployed; a lab AP with forced channel change
  would settle the failure mode.
- **NVS-survives-OTA as a stated guarantee**: universally true in practice
  and implied by the partition model, but not found as an explicit one-line
  guarantee in the NVS or OTA docs this pass [S1010][S1003]. A doc-level
  citation or a factory-reset-behavior note would clean this up.
- **Serial framing prior art**: is there a small, liberally-licensed,
  maintained framing library (COBS/SLIP-style with CRC) conventional in the
  ESP ecosystem worth adopting for the dongle link, or is hand-rolled
  length-prefix framing the field norm? Low stakes; a short survey pass
  would settle it.
