# ADR-014: Mesh group tier — ESP-NOW broadcast as the coordination transport

Status: Proposed (2026-07-09)

## Context

A fourth form factor joins the architecture: **25–50 independent light groups**
(engineering ceiling ~150), each an autonomous ESP32-S3-class fixture rendering
its own effects locally at ~60 fps, deployed outdoors with zero network
infrastructure — no AP, no wires, no designated master. Groups must look
coordinated (shared scene/palette/tempo, waves propagating between neighbors)
while every node stays self-sufficient. The radio carries **state only**
(~11-byte fixed-layout frames at ~10 Hz per node), never pixels. The tier must
interoperate with peer art fleets that already use compact fixed-layout ESP-NOW
broadcasts at this rate, and each node keeps the full Q-* quality pipeline
(ADR-001/002) on-device. RA-13 covers ESP-NOW in depth; RA-14 surveys every
alternative transport on this hardware class.

## Decision

- **ESP-NOW broadcast** (`ff:ff:ff:ff:ff:ff` pseudo-peer), single-hop,
  connectionless, membership-free: every node broadcasts its state frame at
  ~10 Hz and listens promiscuously; no join, no peer table, no routing.
- **Unencrypted broadcast + app-layer integrity** (magic/version byte in the
  fixed layout; app-layer MAC only if spoofing ever matters). This is forced,
  not chosen: the peer table caps at 20 and broadcast cannot be encrypted.
- **One fixed fleet-wide RF channel, baked into firmware** (channel change =
  OTA); frames stay inside the **v1 250 B envelope** so IDF-version mixing is
  a non-issue.
- **Default 1 Mbps rate for the 25–50 node design target.** At the ~150
  ceiling, raise the broadcast peer's TX rate to 6–11 Mbps via
  `esp_now_set_peer_rate_config` — standard-rate receivers (including
  default-config peer fleets) decode raised rates with no change on their
  side. Long Range (LR) mode is **rejected** as a fleet transport (both-ends
  opt-in breaks interop; airtime-saturates at ~50 nodes × 10 Hz); it remains
  a recorded option flag for sparse long-range layouts with the interop
  caveat in RA-14's open questions.
- Radio callbacks follow the copy-and-enqueue discipline (RA-16 task layout);
  send pacing off the send callback.

## Consequences

- The tier is **locked to Espressif silicon**; non-Espressif radios (the
  nRF52840 wearables) participate only through a bridge (ADR-016).
- Broadcast delivery is fire-and-forget — no ACK, no retry; the **10 Hz
  repetition is load-bearing** (a lost frame costs 100 ms of staleness, which
  the coordination layer above is designed to absorb, ADR-015).
- Airtime is the scaling wall: ~31 % channel utilization at 50 nodes ×
  10 Hz × 1 Mbps is comfortable; ~94 % at 150 nodes is not — the ceiling
  **requires** the rate raise (or per-node rate reduction / channel-cell
  partitioning).
- Nodes that also run BLE (config app, wearable bridge) must stay in STA
  mode — ESP-NOW RX under BLE coexistence is only supported there — and
  expect reception gaps.
- No published measurement exists at 25+ senders × 10 Hz; the airtime math
  is computed, not sniffed (prototype item, §12).

## Evidence

- [S800] ESP-NOW official API: broadcast/no-ACK semantics, v1 250 B / v2
  1470 B limits and mixing rules, no encrypted broadcast, callback and
  send-pacing guidance.
- [S806] Frame anatomy (43 B fixed overhead), CSMA/CA, encryption limits,
  measured broadcast PRR ≥99 % under 40 Mbit/s co-channel WiFi at healthy
  RSS, collapse below ~−80 dBm.
- [S817][S804] 802.11b/OFDM timing constants + sniffer-verified 1 Mbps
  default and retry behavior — the inputs to RA-13's airtime table
  (624 µs/frame at 1 Mbps → 31 % @ 50 nodes, 94 % @ 150; 102 µs at 6 Mbps).
- [S802] 20-peer table wall; broadcast escapes it; per-frame sender MAC +
  RSSI delivered to the receive callback.
- [S811] IDF: per-peer rate config API (incl. broadcast pseudo-peer), v2
  constant history (1490→1470), additive-only API changes across IDF 5.x.
- [S807] LR mode: Espressif-proprietary PHY, both ends must opt in, ~4 dB
  gain — the interop breaker.
- [S851][S852] painlessMesh field reports: degradation at 50, collapse at
  72 nodes — inside this tier's target range.
- [S853][S854][S855] ESP-WIFI-MESH/ESP-MESH-LITE: fixed-root SPOF in
  routerless mode; Mesh-Lite has no mesh-wide broadcast domain (NAT
  subnets), 45–50 s self-heal, closed-source core blobs.
- [S860][S861][S862] BLE Mesh: spec origination cap ≈10 msg/s/node (met by
  the heartbeat alone, before relays); 256-node evidence only at ≤0.7
  msg/s; broadcast-storm literature at ~86 dense nodes.
- [S865][S867] Thread/OpenThread: healthy but 250 kbps PHY cannot carry
  10 Hz fleet floods, and S3 needs a C6/H2 companion radio.
- [S869][S870][S150] Infrastructure WiFi + UDP: physics fine at 25–50
  stations, but the AP is the forbidden infrastructure/SPOF.
- [S873][S874] LoRa/LoRaWAN: duty-cycle regulation and ≤11 kbit/s put it
  2–3 orders of magnitude short of 10 Hz fleet state.

## Rejected alternatives

- **painlessMesh** — waning (minimal upstream), GPLv3, field collapse at
  50–72 nodes, JSON-over-TCP tree hostile to a render loop [S850][S851][S852].
- **ESP-WIFI-MESH** — vendor-superseded; routerless mode has an
  unrecoverable fixed-root SPOF [S853][S854].
- **ESP-MESH-LITE** — active but structurally wrong: no mesh-wide broadcast
  (kills the 11-byte interop frame), root SPOF, closed blobs, 45–50 s heal
  [S855][S854].
- **BLE Mesh** — spec-capped at exactly pewpew's origination rate before any
  relaying; flood saturates 3 adv channels at this density [S860][S861][S862].
- **Thread on C6/H2 companion** — PHY-rate wall at 10 Hz floods + second
  radio chip per node; the least-bad mesh if multi-hop ever becomes a hard
  requirement, with on-change (not fixed-rate) discipline [S865][S867].
- **Infrastructure WiFi + UDP broadcast** — disqualified by the
  zero-infrastructure requirement, not physics; the honest fallback where an
  AP is acceptable [S869][S150].
- **802.11 LR as fleet mode** — breaks interop (both-ends opt-in), saturates
  at ~50 nodes × 10 Hz [S807][S868].
- **LoRa/LoRaWAN** — 2–3 orders of magnitude short; sub-1 Hz side channel at
  most [S873][S874].
- **ESP-NOW built-in encryption** — ≤17 encrypted peers and no encrypted
  broadcast make it structurally unusable at fleet scale [S800][S802].
