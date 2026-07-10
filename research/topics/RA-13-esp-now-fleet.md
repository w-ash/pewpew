# RA-13: ESP-NOW protocol & fleet scaling

Last researched: 2026-07-09
Status: draft
S-ID block: S800–S849

## Key questions

- ESP-NOW v1 vs v2: payload limits, which chips/IDF versions support v2, v1/v2 mixed-fleet compatibility.
- Broadcast vs unicast peer semantics: peer-table limits (encrypted vs unencrypted), what broadcast is at the 802.11 layer, ACK/retry semantics, measured broadcast delivery rates.
- Encryption: PMK/LMK model, encrypted-peer limits, can broadcast be encrypted, implications for an art fleet.
- PHY/rate options: default 1 Mbps, `esp_now_set_peer_rate_config`, Long Range (LR) mode, published range measurements.
- Coexistence: ESP-NOW + WiFi STA (channel constraint), + softAP, + BLE; reliability costs.
- Fleet scale: airtime math for N nodes broadcasting ~11 B payloads at ~10 Hz; published node counts; CSMA/CA behavior; congestion failure modes; callback-queue overflows.
- Latency: typical send-to-receive latency and jitter, published measurements.
- API stability: ESP-NOW across IDF 5.x, Arduino-ESP32 3.x wrapper, S3 vs C3/C6 specifics.
- **The verdict question:** is broadcast of ~11-byte state payloads at ~10 Hz/node viable at 50 nodes? At 150?

## Findings

### What ESP-NOW actually is at the 802.11 layer

ESP-NOW is a connectionless Espressif-proprietary protocol carried in IEEE 802.11 **vendor-specific action frames** (management frames, category code 127, Espressif OUI `0x18fe34`), with no association, no IP stack, and no layers above the link layer [S800][S806]. The frame anatomy, with byte counts: 24 B MAC header (frame control 2, duration 2, three 6-B addresses, sequence control 2) + 1 B category + 3 B OUI + 4 B random value (replay protection) + 7 B vendor-IE header (element ID, length, OUI, type, version) + 0–250 B body (v1) + 4 B FCS — a fixed **43 B of protocol overhead** around the payload [S806][S800]. Espressif positions it for one-to-one, one-to-many, and many-to-many control with "millisecond-level delay" and ~200 m open-space range at up to +21 dBm [S801]. It is Espressif-only silicon: ESP8266, ESP32, ESP32-S and -C series [S801]. No non-Espressif chip (e.g. pewpew's nRF52840 wearables) can participate; the independent-groups tier is therefore locked to ESP32-family parts as long as ESP-NOW is the interop transport [S801].

Medium access is the standard 802.11 CSMA/CA DCF: a sniffer study confirmed carrier sensing with p-persistent geometric backoff on retransmissions, ~481 µs average backoff slot spacing, and all traffic sent as 802.11b MPDUs at 1 Mbit/s / 20 MHz under default config [S804]. "The default IEEE802.11 CSMA mechanism is used to avoid collisions" [S806].

**ACK/retry semantics** differ sharply by address type:
- **Unicast** frames are MAC-ACKed and retransmitted on failure. The WONS 2025 sniffer study observed **up to 31 retransmissions** of a single ESP-NOW unicast frame (an older 2018 measurement had found 10), first retransmission ~3.4 ms after the original, subsequent ones spaced by geometric backoff [S804]. The send callback reports `ESP_NOW_SEND_SUCCESS` when the frame "is received successfully on the MAC layer" — i.e. MAC-ACKed — which still does not guarantee the application saw it; Espressif's own guidance is to implement app-layer ack/retry if delivery matters [S800].
- **Broadcast** (and multicast) frames get **no ACK and no retransmission** — this is baseline 802.11 behavior for group-addressed frames under DCF [S817], stated for ESP-NOW explicitly: "No acknowledgment is required for broadcast transmissions" [S806]. A broadcast is transmitted exactly once; collisions and fades convert directly into silent loss, and the send callback's "success" only means the frame left the radio [S800][S806]. For a state-repeated-at-10 Hz design this is the right trade: loss costs one 100 ms update period, never queue-backlog jitter.

### v1 vs v2: payload limits and mixed fleets

- **v1.0**: max payload `ESP_NOW_MAX_DATA_LEN` = **250 B**, a hard limit of the vendor-specific IE length field that "does not support configuration" [S800][S802][S811:components/esp_wifi/include/esp_now.h#L35-L36].
- **v2.0**: max payload `ESP_NOW_MAX_DATA_LEN_V2` = **1470 B** [S800]. Version support is an **IDF-version property, not a hardware property** [S803]: the constant does not exist in IDF v5.3, appears in v5.4 with value **1490**, and is corrected to **1470** in v5.5 and master — verified by diffing `esp_now.h` across release tags [S811]. (Anything built on v5.4 believing 1490 can send frames a v5.5 peer's constant says are oversized; treat 1470 as the real ceiling.)
- **Mixing rules**: "v2.0 devices are capable of receiving packets from both v2.0 and v1.0 devices", while v1.0 devices receive v2.0 packets only if payload ≤ 250 B; longer v2.0 packets are truncated to 250 B or discarded by v1.0 receivers [S800][S811:components/esp_wifi/include/esp_now.h#L150-L151].

Implication for pewpew: the interop fleet's ~11 B state payloads are far below every limit, so v1/v2 mixing is a non-issue for state broadcast — an ~11 B broadcast from an IDF 5.5 node is received identically by IDF 4.x peers [S800]. v2's 1470 B matters only if we later want chunkier payloads (e.g. palette blobs), and then only among our own nodes on IDF ≥ 5.4 [S811][S803].

### Broadcast vs unicast: peer tables and semantics

The peer table caps at `ESP_NOW_MAX_TOTAL_PEER_NUM` = **20 peers total**, of which at most **6–7 encrypted by default** (`ESP_NOW_MAX_ENCRYPT_PEER_NUM` = 6 in the header; the Kconfig default `CONFIG_ESP_WIFI_ESPNOW_MAX_ENCRYPT_NUM` is 7, raisable to **17**) [S811:components/esp_wifi/include/esp_now.h#L32-L33][S800][S802]. A 25–150 node fleet therefore **cannot be built on unicast peer lists at all** — 20 peers is the wall.

Broadcast escapes the wall entirely: the sender registers the single broadcast address `ff:ff:ff:ff:ff:ff` as one peer, and "theoretically there is no limitation in the number of devices" that can listen [S802]. Reception requires no peer registration — Espressif's own broadcast example has receivers accept frames from unknown senders and optionally register them afterwards [S809]. The receive callback delivers sender MAC + RSSI (`wifi_pkt_rx_ctrl_t`) for every frame [S802][S800]. This matches the interop constraint exactly: every node broadcasts its compact state; every node passively hears every neighbor; no pairing, no membership protocol.

### Encryption: PMK/LMK and why the fleet runs unencrypted

ESP-NOW encryption is CCMP (AES-128, per IEEE 802.11-2012) on the action frame body, keyed by a per-peer 16 B **LMK** (Local Master Key); LMKs are themselves encrypted with a device-global 16 B **PMK** (Primary Master Key) [S800]. Two hard limits kill it for fleet use:
1. Encrypted peers cap at 17 (default 6–7) [S800][S802][S811:components/esp_wifi/include/esp_now.h#L33].
2. "Encrypting multicast vendor-specific action frame is not supported" — **broadcast cannot be encrypted, period** [S800]; the literature says the same and points to application-layer pre-shared keys as the recourse [S806].

So the viable posture for an art fleet — and the one the interop peer fleets already use — is **unencrypted broadcast with app-layer integrity**: fixed-layout payload, magic/version byte, and if spoofing ever matters, an app-layer MAC or rolling code. The frame's 4-byte random-values field provides replay resistance at the frame level [S800]. Espressif's own `esp-now` component demonstrates the app-layer pattern (ECDH handshake + AES128-CCM above unencrypted ESP-NOW) for control channels, claiming 16 devices keyed in 5 s [S810]. For light-state beacons, integrity-without-secrecy is sufficient; confidentiality of "what color am I" is worthless.

### PHY rates and Long Range mode

Default rate is **1 Mbps** 802.11b DSSS [S800][S802][S804]. Since IDF 5.x the per-peer API `esp_now_set_peer_rate_config(peer_addr, wifi_tx_rate_config_t)` sets the TX rate for any peer **including the broadcast pseudo-peer** — MCS0–7, legacy 802.11bg rates, or LR — replacing the interface-global `esp_wifi_config_espnow_rate()`, which is marked deprecated in v5.5 ("please use esp_now_set_peer_rate_config() instead"; also "only work when not use Wi-Fi 6") and deleted from master [S811][S800]. Rate is a transmit-side decision: any 802.11bgn receiver decodes any standard rate, so raising our broadcast rate does not require reconfiguring peer-fleet receivers — with the single exception of LR, which is a proprietary modulation both ends must opt into [S807][S806].

**Long Range (LR) mode**: Espressif-proprietary PHY at 0.5/0.25 Mbps, "reception sensitivity gain of LR is about 4 dB larger than that of the traditional 802.11b mode", "theoretically, the transmission distance is about 2 to 2.5 times the distance of 11B"; only Espressif devices ("ESP32 chip series devices (except ESP32-C2)") can send or receive it [S807]. Practitioner folklore of ~1 km line-of-sight derives from Espressif's 2–2.5× claim on top of ~200–400 m 11b ranges [S807][S801][NEEDS-VERIFICATION]. LR breaks interop with any fleet not also configured for LR [S807][S806], and its airtime cost at fleet scale is disqualifying (see arithmetic below).

**Measured range at default settings**: outdoor line-of-sight farmland with 0.95 m antenna height: PDR 99.97 % below 55 m, then non-monotonic collapse (99.85 % at 52 m, 83 % at 58 m, 8.9 % at 60 m, some good links out to 65 m, nothing at 70+ m); small antenna-position changes moved links between near-perfect and dead [S804]. An IEEE field study measured usable links to ~180 m with loss "substantial" beyond, and 99 % PER at 300 m [S813]. Indoor, at 20 dBm through an office floor, broadcast PRR tracked RSS: 98–100 % at ≥ −72 dBm, ~80 % at −80 dBm, ~30 % at −92 dBm [S806]; a separate 8-node indoor unicast deployment found only about half of through-wall node placements reliable [S805]. **RSS and obstruction, not congestion, dominate loss at these fleet sizes** [S805][S806][S804].

### Coexistence: WiFi STA, softAP, BLE

- **Channel lock**: ESP-NOW transmits on whatever channel the STA/softAP interface occupies; when the station is associated to an AP, "the channel of ESP-NOW must be the same as that of the connected AP" [S802][S800]. WLED's tracker states the practical consequence: nodes not on the AP's channel simply never hear the broadcasts, and the only workaround is disconnect–send–reconnect [S815]. For pewpew: a fleet that also joins venue WiFi inherits the venue AP's channel (and its channel-hopping); a WiFi-free fleet should pin one channel fleet-wide as the interop convention.
- **softAP**: ESP-NOW can send from either the STA or softAP interface; the interface must be up and the channel is that interface's channel [S800].
- **BLE coexistence**: ESP32-S3 has **one 2.4 GHz RF chain**; WiFi and BLE time-share it — "a module cannot receive or transmit data while another module is engaged in data transmission or reception", arbitrated by dynamic priorities keyed to WiFi state [S812]. Espressif's coexistence matrix marks ESP-NOW **TX stable ("Y") alongside BLE**, but ESP-NOW **RX "stable in STA mode, otherwise not supported"** [S812]. Since ESP-NOW receive is the whole point of a listening fleet, nodes that also run BLE (e.g. for a config app) must stay in STA mode, enable `CONFIG_ESP_COEX_SW_COEXIST_ENABLE`, and expect reception gaps while BLE is active [S812]. Broadcast's no-retry nature means those gaps are unrecoverable losses — another reason the 10 Hz repeat rate is load-bearing.

### Latency and jitter

- Driver hand-off to first bit on air: **2.67–2.78 ms for a 250 B payload at 1 Mbps** [S804]; airtime scales with payload, so an 11 B state frame is ~0.6 ms on air (624 µs, computed below) plus sub-ms driver time.
- Application-to-application: **5–7 ms typical** for small broadcasts in an uncongested channel [S814]; a field study measured **5.13–46 ms** across distances (unicast, retransmission-inflated at range) [S813]; prior controlled measurements: 1.06 ms for 1 B and 1.87 ms for 100 B payloads [S804]. Espressif's marketing figure is "millisecond-level delay" [S801].
- Jitter sources: unicast retransmissions add ~3.35 ms steps up to 31 deep — delay ECDFs show plateaus at each retransmission slot and tails past 50 ms at marginal RSS [S804]. Broadcast has no retransmissions, so its latency is essentially bounded at the few-ms scale; loss replaces jitter [S806][S817]. Send-side queue backlog is the other jitter source: one report saw normal 5–7 ms balloon to 50–200 ms when sends were spaced < 20 ms apart [S814]; BLE coexistence pauses add stalls on dual-role nodes [S812].
- Against pewpew's budget: at a 10 Hz state rate the update period (100 ms) dwarfs transport latency (~1–7 ms). ESP-NOW latency is a rounding error for state-only coordination; it would only matter if we ever tried frame-synchronous triggering through it (a ~5 ms one-way skew is still under one 60 fps frame).

### Fleet-scale airtime arithmetic — the verdict question

Constants: 43 B protocol overhead per frame [S806]; default PHY 1 Mbps 802.11b DSSS with 192 µs long PLCP preamble+header; DIFS 50 µs, slot 20 µs, CWmin 31 (mean initial backoff 15.5 × 20 = 310 µs, overlapping across contenders); group-addressed frames are never ACKed or retried [S817][S804].

**Per-frame airtime, 11 B payload → 54 B MPDU:**

| PHY rate | preamble | MPDU time | total on-air |
|---|---|---|---|
| 1 Mbps (default) | 192 µs | 432 µs | **624 µs** |
| 11 Mbps (802.11b short) | 96 µs | 39 µs | **135 µs** |
| 6 Mbps (ERP-OFDM) | 20 µs + 6 µs ext | 76 µs | **102 µs** |
| LR 0.25 Mbps | ≥192 µs | 1728 µs | **≳1.9 ms** |

(OFDM row: 19 symbols × 4 µs for 454 bits incl. 22 service/tail bits. Rates/preambles per [S817]; 1 Mbps default and LR rates per [S804][S807].)

**Channel utilization, N nodes × 10 Hz broadcast (raw airtime; +50 µs DIFS each in parens):**

| N | frames/s | @1 Mbps | @11 Mbps | @6 Mbps | @LR 0.25 |
|---|---|---|---|---|---|
| 25 | 250 | 15.6 % (16.9 %) | 3.4 % | 2.6 % | ~48 % |
| 50 | 500 | **31.2 % (33.7 %)** | 6.8 % | 5.1 % | ~96 % — saturated |
| 150 | 1500 | **93.6 % (101 %) — saturated** | 20.3 % | 15.3 % | impossible |

Three structural observations. (1) **Overhead dominates**: at 1 Mbps, preamble + 43 B overhead cost 536 µs of the 624 µs — 86 % of airtime; shrinking the 11 B payload buys nothing, and growing it to ~50 B would only raise per-frame cost to 936 µs. (2) **The default rate is the whole problem**: the same fleet that saturates the channel at 1 Mbps uses ~15 % of it at 6 Mbps. (3) **LR mode is airtime-catastrophic** at fleet scale — 50 nodes at 0.25 Mbps already saturate [S807 rates; arithmetic ours].

**Verdict at 50 nodes, all-default (the interop case): viable.** ~31–34 % utilization leaves CSMA in a stable operating regime; measured support: broadcast PRR stayed ≥ 99 % even with 40 Mbit/s of co-channel WiFi traffic at healthy RSS [S806], and the closest published fleet datapoint — 13 nodes × 10 msg/s ≈ 130 msg/s — reported ~20 % loss in the field, attributed to congestion but plausibly RSS-confounded [S816][NEEDS-VERIFICATION]. Expect single-digit-to-~20 % loss on weak links; at 10 Hz repetition a lost state beacon costs 100 ms of staleness, which neighbor-state effects absorb invisibly.

**Verdict at 150 nodes, all-default: not viable.** 94 %+ raw airtime is past DCF's stable region; broadcast loss becomes severe and, with no retries, unrecoverable. The design ceiling requires at least one of: (a) **raise the broadcast peer's TX rate** on our nodes via `esp_now_set_peer_rate_config` (6–11 Mbps drops us to 15–20 % at 150 nodes; standard receivers, including default-config peer fleets, decode it without any change) [S811:components/esp_wifi/include/esp_now.h#L283][S807]; (b) **lower per-node beacon rate** (150 nodes × 4 Hz @1 Mbps ≈ 37 % — back in bounds); (c) channel-partition the venue into cells. Mixed interop arithmetic works out: 50 legacy peer nodes at defaults (31 %) + 100 pewpew nodes at 6 Mbps/10 Hz (10 %) ≈ 42 % raw — hot but workable [computed from S806/S817 constants].

### Congestion failure modes and callback discipline

- **Send-queue overflow**: `esp_now_send` returns `ESP_ERR_ESPNOW_NO_MEM` when internal buffers fill; Espressif's guidance is to pace sends off the send callback (next send only after the previous callback fires) and back off on NO_MEM [S800]. Ignoring this converts congestion into 50–200 ms latency excursions before it becomes loss [S814].
- **Callback context**: both callbacks run on the high-priority WiFi task; "do not do lengthy operations in the callback function. Instead, post the necessary data to a queue and handle it from a lower priority task" [S800]. At 50-node scale each node's receive callback fires ~500×/s; the copy-to-queue must stay microsecond-cheap or the WiFi task starves — this is the RA-16 render+radio coexistence interface.
- **Out-of-order send callbacks**: official guidance warns that too short an interval between two sends "may lead to disorder of the sending callback function" — send the next frame only after the previous send callback has returned [S802][NEEDS-VERIFICATION — wording surfaced via search index of Espressif docs; confirm exact location on next pass].
- **Hidden nodes**: CSMA only defers to transmitters it can hear; at venue scale, node clusters out of carrier-sense range of each other collide invisibly at the receiver in the middle. No ESP-NOW-specific measurements found; flagged in Open questions.

### API stability & ecosystem status

| System | License | Maintenance (as of 2026-07-09) | Notes |
|---|---|---|---|
| ESP-NOW in ESP-IDF | Apache-2.0 [S811] | Actively developed: v2 added in IDF v5.4, payload constant corrected in v5.5, rate API modernized, old rate API deleted on master (IDF 6.x line) [S811] | Core API (init/add_peer/send/recv) unchanged across IDF 5.x → 6.x; changes are additive [S811][S800] |
| espressif/esp-now app component | Apache-2.0 | Last commit 2026-02-04; 766 stars; User Guide targets IDF v4.4–v5.2 — lags current IDF [S810] | Useful as pattern reference (app-layer security, ESP-NOW OTA: "50 devices … upgraded in 3 minutes"), not as dependency [S810] |
| Arduino-ESP32 ESP_NOW wrapper (3.x) | LGPL-2.1 | Active (pushed 2026-07); class-based API in 3.x [S809] | Still v1-only 250 B cap as of Apr 2025 (issue #11261, PR #11524 pending) [S803] |
| WLED ESP-NOW usage | EUPL-1.2 | ESP-NOW remote (WiZmote) since 0.14.0-b3 (2023-06); packet/byte-format work through 2024 [S808][S818] | Remote-control only; WLED sync remains UDP-over-WiFi; broadcast-channel flexibility is an open feature request [S818][S815] |

Chip specifics: ESP-NOW is supported across ESP32, S2/S3, C2/C3/C5/C6/C61 — the IDF docs page exists per-chip and the header is chip-independent [S800][S811]. Wrinkles: LR mode excludes ESP32-C2 [S807] and its status on WiFi-6 chips (C6) is unclear (open question); on WiFi-6 parts the deprecated global rate API explicitly does not work with HE rates — use the per-peer API [S811]. ESP32-S3 (pewpew's node class) is fully covered including v2 on IDF ≥ 5.4 [S800][S811].

## Verdicts

- **ESP-NOW (IDF core API) — ascendant.** Actively invested by the vendor (v2 payloads in 5.4, per-peer rate config, WiFi-6-aware API cleanup on the 6.x line); API stable across IDF 5.x with additive-only changes; entire ecosystem (WLED remotes, peer art fleets, IoT literature) standardizing on it [S811][S800][S818].
- **ESP-NOW v2 (1470 B payloads) — ascendant but young.** IDF ≥ 5.4 only, constant churned 1490→1470 between 5.4 and 5.5, Arduino wrapper hasn't caught up; design for 250 B interop frames and treat v2 as headroom [S811][S803].
- **Broadcast-of-state at default rate — stable and fit for purpose at ≤50 nodes.** 31 % airtime at 50 × 10 Hz; measured broadcast PRR ≥ 99 % under co-channel load at healthy RSS; loss is graceful (100 ms staleness) [S806][S817][S804].
- **Default 1 Mbps at 150 nodes — not viable; per-peer rate config is the escape hatch.** 94 % airtime saturates; 6–11 Mbps broadcast returns 5–7× headroom and stays receivable by default-config peer fleets [S817][S811][S807].
- **Long Range (LR) mode — stable niche, rejected for fleet broadcast.** Real 4 dB/2–2.5× range gain, but Espressif-only-both-ends, breaks interop, and airtime-saturates at ~50 nodes × 10 Hz [S807][S806].
- **ESP-NOW encryption (PMK/LMK) — stable, rejected at fleet scale.** ≤17 encrypted peers and no encrypted broadcast make it structurally unusable for a 25–150 node broadcast fleet; unencrypted broadcast + app-layer integrity (the peer fleets' existing posture) is correct [S800][S802][S806].
- **espressif/esp-now app component — stable/lagging.** Good pattern quarry (OTA, ECDH-over-ESP-NOW), pinned to IDF ≤ 5.2 docs; do not take as dependency [S810].
- **Arduino-ESP32 ESP_NOW wrapper — stable/lagging.** Fine for remotes/prototypes; fleet nodes should use the IDF API directly for rate config and v2 [S803][S809].

## Code-reading queue

1. **espressif/esp-idf `examples/wifi/espnow`** [S811 pin] — the canonical send/receive task structure: queue between callbacks and worker task, send pacing off the send callback, broadcast-peer setup, and how `wifi_tx_rate_config_t` is populated for the broadcast peer. Answers: the exact skeleton pewpew's node radio task should copy, and how to set 6 Mbps broadcast on IDF 5.5.
2. **espressif/esp-now `src/espnow/` + `src/security/`** [S810, pinned 4432294] — Espressif's own app-layer reliability: retransmission counts for "reliable" sends, group addressing, magic/version framing, ECDH key exchange over unencrypted broadcast, and the ESP-NOW OTA chunking protocol. Answers: what an app-layer integrity/OTA design looks like when the vendor builds it; note IDF ≤ 5.2 assumptions and standard-OTA interop constraint (pewpew must NOT adopt mesh-gossiped OTA).
3. **wled/WLED `wled00/remote.cpp` (+ ESP-NOW init in `network.cpp`)** — how a mainstream firmware consumes third-party fixed-layout ESP-NOW payloads (WiZmote 13 B messages): payload validation, MAC filtering, channel handling while STA-connected. Answers: robust receive-side patterns for exactly pewpew's interop payload style [S808][S818].
4. **espressif/arduino-esp32 `libraries/ESP_NOW/`** — what the 3.x class wrapper adds/hides (peer objects, broadcast class, 250 B cap); decide whether fleet firmware needs raw IDF. Answers: cost of the convenience layer [S809][S803].

## Open questions

- **Broadcast PDR vs offered load at 50–150 nodes**: no published measurement beyond a bot-walled 13-node/130 msg/s/~20 %-loss forum report [S816][NEEDS-VERIFICATION]. Settled by: bench with 10–20 senders emitting 11 B beacons at 10 Hz while a monitor-mode sniffer counts per-sender delivery at 1/6/11 Mbps; extrapolate with the airtime model above.
- **Hidden-node loss at venue scale**: CSMA defers only within carrier-sense range; no ESP-NOW-specific hidden-node measurements found. Settled by: three-cluster field test (A–B mutually hidden, receiver between) with per-sender sequence counting.
- **Beacon phase alignment**: do fixed-period 10 Hz senders drift into repeating collision patterns, and does CSMA fully break the alignment? Settled by: same bench as above, comparing fixed-period vs ±10 % jittered send timers.
- **Send-callback semantics for broadcast**: does the callback ever report FAIL for a broadcast (e.g. TX abort), or is it always SUCCESS? The binary WiFi blob is closed; docs are silent. Settled by: bench test with forced channel jamming; matters for send-side health metrics.
- **LR mode on ESP32-S3/C6 specifically**: the LR doc is written for classic ESP32 ("ESP32 chip series devices (except ESP32-C2)") [S807]; an open Espressif tracker item questions LR on C6. Moot if LR stays rejected, but settle via chip-specific docs/bench before ever revisiting.
- **Exact 20 %-loss thread contents** [S816]: esp32.com is behind a bot challenge; figures came from search-index excerpts. Settled by: re-fetch from another network, or replicate the 13-node experiment directly (better).
- **RSSI-based fleet ranging**: `.forward_rssi`-style neighbor filtering is mentioned in the FAQ [S802] — whether per-frame RSSI is stable enough to gate "neighbor" status for effects is untested; RA-15's territory, bench data needed.
- **Peer-fleet payload headroom**: whether the interop fleet's ~11 B fixed layout tolerates trailing extension bytes (v1 payloads up to 250 B) without confusing their parsers — requires reading the peer fleet's parser or asking; protocol-level docs cannot answer it.
- **Airtime constants are computed, not measured**: the 624 µs/frame figure follows from [S817] timing plus the [S806] frame layout; a sniffer capture (as in [S804]) of an actual 11 B broadcast would confirm preamble mode (long vs short) and any padding within an afternoon.
