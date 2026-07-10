# ADR-016: Mesh group tier — host gateway, fleet ops, and the wearable BLE bridge

Status: Proposed (2026-07-09)

## Context

The mesh tier is host-optional (M-5), but when the Python host is present it
must inject live parameter edits (ADR-015 Layer 1) and collect telemetry —
through some bridge between IP-land and the ESP-NOW broadcast domain. The
governing constraint: ESP-NOW transmits on the WiFi interface's channel, and
a STA associated to an AP is locked to that AP's channel — so a WiFi-attached
gateway chains the *entire fleet's* channel to the venue AP. Separately, the
fleet needs an OTA/provisioning story at 25–150 nodes, and the wearable tier
(nRF52840, no ESP-NOW radio, ADR-008) needs a way to receive group state
without wrecking its power budget. RA-17 (gateway/ops) and RA-18 (wearable
bridge) supply the evidence.

## Decision

**Gateway — primary: USB serial dongle on the host.** An ESP32-S3 board
running thin firmware: length-prefixed frames over USB-CDC ↔ ESP-NOW
broadcast. This is Espressif's own first-party example topology and the
decade-proven Zigbee-coordinator model; it frees the fleet channel from any
venue AP, keeps the command path in low single-digit ms, and is exactly as
optional as the host — unplug it and the mesh continues.
**Fallback: single-chip WiFi-STA + ESP-NOW gateway** (works since IDF 5.0)
for deployments where the host cannot be physically near the mesh; accept
the venue-channel coupling, `WIFI_PS_NONE`, and connect-before-init ordering
pitfalls. **Rejected: two-radio custom gateway** (no maintained precedent; a
Pi + dongle reproduces it from stock parts).

**Telemetry:** downlink is broadcast-only (parameter epochs); uplink is
phase-offset node status beacons every 10–30 s (~15 frames/s at 150 nodes —
negligible airtime) carrying version, battery/rail state, and health.

**Fleet OTA:** standard IDF dual-slot OTA with rollback
(`esp_ota_mark_app_valid_cancel_rollback`) and signed app images without
secure boot, run in deliberate maintenance windows over a temporary WiFi AP.
**No mesh-gossiped firmware distribution.** Nodes self-report their running
version (`esp_app_desc_t`) via telemetry, so a node that missed the window is
visible, not mysterious. The espressif/esp-now component's ESP-NOW OTA ("50
devices in 3 minutes", resumable) is the recorded escape hatch if windowed
WiFi OTA proves too slow.

**Provisioning:** zero-touch — factory eFuse MAC is node identity; NVS
separates config from firmware and survives OTA; an unencrypted broadcast
fleet has no join step. The one provisioned datum is the RF channel, baked
into firmware (channel change = OTA) rather than runtime-mutable, avoiding
stranded-node failure modes.

**Wearable bridge:** one (or more — state is idempotent, receivers take any
copy) dedicated **non-rendering ESP32-S3 bridge node, WiFi in STA mode with
coexistence enabled**, receiving mesh broadcasts and re-emitting the latest
group state as **legacy non-connectable BLE advertisements (Manufacturer
Specific Data**, ~27 usable bytes — 2× headroom) at a 50–100 ms interval.
Wearables keep the ADR-008 stack unchanged and add a **passive,
prefix-filtered, duty-cycled `_bleio` scan** (30 ms/1 s active ≈ 0.2 mA;
30 ms/5 s idle ≈ 0.04 mA). **State tier: scene/palette/tempo yes (freshness
≤1–2 s at sub-percent radio duty); beat-phase no** — advertising `advDelay`
jitter, scan aliasing, and interpreter GC cap phase error at tens of ms, so
wearables free-run a local beat clock disciplined by the gossiped tempo, and
tight-phase effects stay on the mesh tier. RP2350 (non-radio) wearables stay
standalone; group participation is a reason to pick the nRF52840 variant.

## Consequences

- The host's mesh presence is a $10 dev board and a USB cable; no fleet
  reconfiguration when the host arrives or leaves (M-5 preserved).
- The fallback gateway inherits a disputed platform behavior (STA-associated
  nodes possibly BSSID-filtering ESP-NOW broadcasts) — bench item before it
  ships (§12).
- Maintenance-window OTA trades update latency for observability and node
  fungibility; a version-skewed fleet is expected transiently and telemetry
  makes it visible.
- The bridge is a new (cheap) fixture class; its ESP-NOW loss rate under BLE
  advertising coexistence is unmeasured — bench-gated, with the two-chip
  UART bridge as the recorded escalation if loss >~20 %.
- Wearables never join the ESP-NOW domain; the tier's Espressif lock
  (ADR-014) stops at the bridge.

## Evidence

- [S1000] Espressif FAQ/docs: ESP-NOW channel must equal the STA's AP
  channel; no post-association channel switching — the constraint that
  decides the gateway pattern.
- [S1001] espressif/esp-now component (Apache-2.0, active 2026-02): ships
  the UART↔ESP-NOW dongle as its get-started example, plus resumable
  ESP-NOW OTA ("50 devices … 3 minutes") — first-party precedent for both
  the primary gateway and the OTA escape hatch.
- [S1015] ZHA/Zigbee serial-coordinator model — a decade of ecosystem
  precedent for radio-dongle-on-host.
- [S1002][S1012] Single-chip STA+ESP-NOW tutorials + pitfalls (power save,
  init ordering; the disputed BSSID broadcast-filter claim).
- [S1003] IDF OTA: dual-slot + rollback + signed apps without secure boot;
  `esp_app_desc_t` version introspection [S1013].
- [S1006] painlessMesh's own tracker: mesh OTA reboots nodes "without any
  chance for the gateway to know what is going on" — the observability
  failure that justifies windowed OTA.
- [S1005] ESP-MESH-LITE OTA: supported but demands RAM/topology tuning —
  the complexity cautionary tale.
- [S1011][S1010] eFuse base MAC as identity; NVS config/firmware separation.
- [S1050] BLE legacy advertising: ~27 usable MSD bytes (2× the state
  payload); extended advertising unnecessary.
- [S1053] Espressif coexistence matrix: WiFi-STA + BLE advertising stable;
  ESP-NOW RX "stable in STA mode, otherwise not supported"; SoftAP+BLE
  unstable — dictates the bridge's radio mode.
- [S1059] BT 5 non-connectable advertising floor 20 ms (BT 4.x: 100 ms) —
  the bridge can re-emit at/above the mesh's 10 Hz.
- [S1051][S1052] Nordic: nRF52840 radio RX 6.26 mA typ; continuous scan
  ~6.5 mA; duty-cycling is the lever — 30 ms/1 s ≈ 0.2 mA average.
- [S1055][S1056] CircuitPython `_bleio` observer role (interval/window/
  prefix filter); adafruit_ble MIT, active (10.1.3, 2026-04-23);
  BroadcastNet as in-ecosystem connectionless-MSD precedent [S1060].
- [S1057][S1062] advDelay 0–10 ms per advertising event (non-disableable) +
  historical unfiltered-scan MemoryErrors — the beat-phase cap and the
  filtered-burst-scan discipline.
- [S1054][S1058] ESP-NOW connectionless power save: real but ~19.5–20.7 mA
  average on S3 — 5× better than SoftAP, still ~2 orders above the BLE
  observer; kills ESP-NOW-only wearables.

## Rejected alternatives

- **Two-radio custom gateway (ESP-NOW chip + WiFi/Ethernet chip, UART)** —
  no maintained precedent; reproduced from stock parts (Pi + dongle) if ever
  needed [RA-17 pattern C].
- **Mesh-gossiped OTA** — observability and fungibility losses documented by
  its own practitioners [S1006][S1005].
- **Runtime-mutable RF channel via broadcast command** — a node that misses
  the command is stranded; firmware-constant + OTA is self-healing [S1000].
- **ESP-NOW-only wearables (connectionless power save)** — honest check
  done: ~20 mA average, ~30–100× the BLE observer budget, and abandons the
  CircuitPython/nRF52840 stack [S1054][S1058].
- **Nordic ESB for wearable sync** — nRF-only silicon interop, no
  CircuitPython exposure, still needs a bridge anyway [S1063].
- **LoRa on-body** — ~1 % regulatory duty cycle vs 10 Hz state [S1064].
- **ESP32-C6 as bridge silicon** — same time-sliced single radio, fewer
  cores; S3 wins on fleet homogeneity [S1065].
- **Phone-as-bridge (GATT relay)** — degenerate fallback, out of scope this
  pass [RA-18 open questions].
