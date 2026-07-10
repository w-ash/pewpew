# RA-14: Mesh/transport alternatives for low-rate group state

Last researched: 2026-07-09
Status: draft
S-ID block: S850–S899

## Key questions

- For 25–50 (ceiling ~150) autonomous ESP32-S3 light-group nodes exchanging
  ~11-byte state messages at ~10 Hz outdoors with zero fixed infrastructure,
  which transports other than ESP-NOW (covered in RA-13) are viable?
- painlessMesh: license, maintenance status in 2026, scaling ceiling, heap
  behavior, coexistence with LED rendering.
- ESP-WIFI-MESH (IDF component): tree topology mechanics, root election,
  Espressif's claimed node counts vs. real experience, latency per hop.
- ESP-MESH-LITE: how it differs from ESP-WIFI-MESH, maintenance/adoption.
- BLE Mesh: flood-relay latency, node counts on ESP32, provisioning burden,
  fit for unprovisioned broadcast of tiny state.
- Thread/OpenThread on ESP32-C6/H2: border-router requirement, latency,
  whether a C6 companion radio next to an S3 makes sense; Matter relevance.
- Infrastructure WiFi + UDP broadcast/multicast via a portable AP: loss
  characteristics for tiny periodic state, AP client-count limits at 50–150
  stations, portable-router practicality.
- 802.11 LR (Espressif Long Range): what it is, throughput/range tradeoff,
  vendor lock.
- LoRa/LoRaWAN: disqualifying at ~10 Hz? (brief)
- Which transports remain viable, and which are disqualified and why?

## Findings

Scope note: ESP-NOW itself is covered in RA-13. This document covers every
other candidate transport for the autonomous-group tier and ends with a
comparison against the ESP-NOW baseline. The workload under evaluation is
deliberately tiny: ~11-byte fixed-layout state payloads at ~10 Hz from each
of 25–50 nodes (design ceiling ~150), no streamed pixels, no time-sync
requirement, outdoors, zero fixed infrastructure.

### painlessMesh

**What it is.** Arduino/PlatformIO library for ESP8266/ESP32 that builds a
"true ad-hoc network" — "no-planning, central controller, or router is
required" — by running every node as simultaneous softAP + STA and forming a
tree of TCP connections (default port 5555) over ordinary WiFi
[S850:README.md]. Nodes are addressed by 32-bit chip ID; messages are
broadcast or single-target, encoded as JSON; the library maintains a common
time base via "an SNTP based protocol" and can measure per-node trip delay
[S850:README.md]. Routing/topology maintenance is automatic; the layered
mesh protocol lives in `src/painlessmesh/` (connection, router, ntp, layout
modules) [S850].

**License.** GPLv3 [S850:LICENSE]. This is the only copyleft candidate in
this survey; linking it into pewpew group-node firmware would put that
firmware under GPLv3 distribution obligations.

**Scaling evidence — the weakest of any candidate.** The README itself
hedges: "The maximum size of the mesh is limited (we think) by the amount of
memory in the heap that can be allocated to the sub-connections buffer"
[S850:README.md], and warns to "be conservative in the number of messages
(and especially broadcast messages) you sent per minute … Both esp8266 and
esp32 are limited in processing power/memory, making it easy to overload the
mesh and destabilize it," and that "Messages can go missing or be dropped
due to high traffic and you can not rely on all messages to be delivered"
[S850:README.md]. Every node stores the full topology (JSON sub-connection
tree), so state grows with network size on every node [S850][S852]. The most
directly relevant field data: a 72-node ESP8266 experiment reported the mesh
"working on 36 nodes", degraded at 50 nodes ("26 nodes available within the
mesh network"), and collapsed at 72 nodes ("0 nodes available") — with
substantial free heap remaining, i.e., the failure was protocol/CPU
overload, not raw memory [S851]. A separate issue reports a 60-node build
where "only 40-44 nodes successfully connected, with older nodes
disconnecting as new ones joined", the reporter noting the
`subConnectionJson` topology string had already reached ~1200 bytes; the
target of 200 nodes went unanswered [S852]. These numbers straddle exactly
pewpew's 25–50 target and sit far below the ~150 ceiling.

**Coexistence with LED rendering.** painlessMesh requires the sketch to
avoid `delay()` and cooperate with its TaskScheduler-driven background tasks
or "the mesh [can] lose stability/fall apart" [S850:README.md]; JSON
serialization per message adds CPU cost the README itself flags as a known
inefficiency ("Some performance is lost") [S850:README.md]. A 60 fps render
loop plus JSON mesh maintenance on one core is exactly the overload scenario
the README warns about [S850][S851].

**Maintenance status (2026).** Not dead, but slow: the canonical repo moved
from GitHub to GitLab (the GitHub `gmag11/painlessMesh` copy is an explicit
mirror) [S857]; last release v1.5.7 on 2025-10-01, last repository activity
2026-06-14, not archived [S850]. Release cadence is a handful of patch
releases per year by a small maintainer group. A third-party fork
(`Alteriom/painlessMesh`, GPL-3.0, releases through v1.9.20 on 2026-03-27)
is more active but has negligible adoption (9 stars) and is not the library
the ecosystem installs [S856]. Net: maintained-in-name, waning-in-practice.

### ESP-WIFI-MESH (a.k.a. ESP-MESH, ESP-IDF built-in)

**What it is.** Espressif's own WiFi-layer mesh, shipped in ESP-IDF as the
`esp_mesh` component. Nodes run softAP + STA simultaneously; each node holds
"a single upstream connection using its station interface" and "multiple
downstream connections using its softAP interface", which "naturally
result[s] in a tree network topology" — it is a tree, not a true mesh; there
are no lateral links [S853]. Packets are addressed by MAC address and
forwarded up/down the tree via routing tables; the whole network sits on one
WiFi channel [S853].

**Root election and the no-router catch.** In self-organized mode the root
is elected by comparing each candidate's RSSI *to the router*: nodes
broadcast their router-RSSI, and a node becomes root once it sees "a vote
percentage larger than a preconfigured threshold (90% by default)" [S853].
That election signal **requires a router to exist**. A "no-router" mode is
supported (Espressif ships a no-router example), but there the root must be
user-designated (`esp_mesh_fix_root()` on all other nodes), and Espressif's
own FAQ states the disqualifying caveat plainly: in the no-router solution,
"if the root node crashes, the other devices will not be able to recover"
[S854]. For a battery-powered outdoor fleet with zero infrastructure, a
non-self-healing single point of failure at the root is a structural
mismatch.

**Scaling and latency.** Network size "is dependent on the maximum number
of layers permitted … and the maximum number of downstream connections each
node can have"; Espressif's published performance figures — network build
< 60 s, root-failure healing < 10 s, child-failure healing < 5 s, per-hop
packet delay 10–30 ms — were measured on a 100-device network configured
for 6 downstream connections and 6 layers [S853]. So 100+ nodes is
demonstrated by the vendor, comfortably above pewpew's ceiling. Espressif's
FAQ claims ESP32 Wi-Fi mesh "can support 1,000 devices" though it recommends
staying under 512 per network [S854]. Worst-case state-message latency
between two leaves in a 6-layer tree is ~10 hops ≈ 100–300 ms by the
vendor's own per-hop figure [S853] — tolerable for 10 Hz state but an order
of magnitude worse than a single broadcast hop.

**Maintenance status (2026).** Part of ESP-IDF (Apache-2.0), maintained by
Espressif; present through IDF v5.x/v6.0 docs [S853]. However, Espressif's
FAQ now says: "If you have new requirements for Wi-Fi Mesh applications, it
is recommended to use our newly released ESP-Mesh-Lite solution, instead of
Wi-Fi Mesh" [S854] — the vendor itself is steering new designs away.
Stable-but-superseded.

### ESP-MESH-LITE

**What it is.** Espressif's newer WiFi mesh, distributed as a managed
component (`espressif/mesh_lite`) in the esp-mesh-lite repository, built on
the esp-iot-bridge softAP+STA NAT machinery rather than the `esp_mesh`
MAC-layer forwarding [S855:components/mesh_lite/User_Guide.md]. Same
physical shape — softAP+STA tree, beacon-advertised Vendor IE metadata,
preferred-parent selection by layer then RSSI — but forwarding happens at
the **IP layer**: "each node gets an IP address assigned by its parent node,
hence accessing the network in the same way a single device accesses a
router", and "sub-devices in the network [can] independently access the
external network" through chained NAT [S855:components/mesh_lite/User_Guide.md].
Configurable to 15 layers and 10 downstream connections per node
[S855:components/mesh_lite/User_Guide.md].

**Consequence of IP-layer NAT for pewpew's traffic pattern.** Each softAP
cell is its own NAT'd subnet. A UDP broadcast emitted by one node reaches
only its own cell (its parent's softAP subnet or its own children); there is
no mesh-wide L2 broadcast domain. Mesh-wide state dissemination must
therefore go through Mesh-Lite's own communication API (JSON messages with
per-hop forwarding over bound UDP/TCP sockets, visible as the
`ESP_Mesh_Lite_Comm` ports in the no-router example log)
[S855:examples/no_router/README.md]. The ~11-byte fixed-layout broadcast
interop constraint cannot be satisfied natively; a gateway/translation layer
would be required.

**No-router mode.** Exists as a first-class example, but one device must be
statically configured as root via menuconfig ("all the devices are non-root
nodes by default"; "There is only one root node") [S855:examples/no_router/README.md];
automatic root election is described only in terms of comparing router-RSSI
after "connecting to the configured Wi-Fi router"
[S855:components/mesh_lite/User_Guide.md]. The FAQ's no-router caveat — a
designated root that crashes strands the network [S854] — applies here too.

**Scaling and latency.** Vendor performance metrics: provisioning < 60 s,
per-hop delay 8–12 ms, but repair times of "Root node disconnection: < 50
seconds" and "Child node disconnection: < 45 seconds", measured on a
50-device network at 6 downstream connections / 6 layers
[S855:components/mesh_lite/User_Guide.md]. A 45–50 s self-heal is a long
visible outage for a live light show, and markedly worse than ESP-WIFI-MESH's
published < 10 s [S853].

**License / openness.** The repository's license text is Apache-2.0, but the
mesh core ships **only as precompiled static libraries**
(`libesp_mesh_lite_esp32*.a` for ESP32/C2/C3/C6/S2/S3) — the actual mesh
implementation is closed-source binary blobs; only glue and examples are
source [S855:components/mesh_lite/lib]. Debugging fleet-scale radio behavior
against a binary blob is a real cost, and it is a hard Espressif lock-in.

**Maintenance status (2026).** Active: Espressif's recommended path for new
Wi-Fi-mesh designs [S854]; repository pushed 2025-09-30, mesh_lite libs
updated 2025-09-15 [S855]. Ascendant within its niche — but its niche is
"many IoT devices sharing one internet uplink", not peer state broadcast.

### BLE Mesh (Bluetooth SIG mesh)

**What it is.** The Bluetooth SIG's standardized mesh: nodes broadcast small
network PDUs on the three BLE advertising channels (37/38/39) and designated
relay nodes re-broadcast them — "managed flooding", not routing; propagation
is bounded by a TTL field, a message cache suppresses re-relaying, and
sequence numbers provide replay protection [S862][S864]. Theoretical maximum
network size is 32,767 nodes, which the SIG itself calls out as the wrong
question — the real limit is "the maximum, total number of mesh messages per
second which can be communicated between nodes in direct radio range"
[S862].

**Payload fit.** An unsegmented (single-advertisement) message carries "a
maximum unsegmented payload of up to 15 bytes" at the transport layer
[S863], of which 11 octets are access-layer payload — opcode plus
parameters (10 parameter octets with a 1-octet vendor opcode)
[S864][NEEDS-VERIFICATION] (exact octet split to be checked against the
spec's lower-transport tables — see Open questions). pewpew's ~11-byte
state payload therefore sits exactly at the unsegmented boundary; anything
larger triggers segmentation and acknowledged reassembly, which is where BLE
mesh latency degrades sharply [S860].

**The rate problem — this is the disqualifier.** The SIG specification
bounds origination: "A node should originate less than 100 Lower Transport
PDUs in a moving 10-second window" [S862] — i.e., ≤10 messages/s per node,
meaning pewpew's ~10 Hz heartbeat sits at the spec's maximum permitted
origination rate before a single relay repeat is counted. Flooding then
multiplies traffic: "the inclusion of ten relays will more or less multiply
the number of packets in the whole network by ten" [S862]. At 25–50 nodes
each originating 10/s, network-wide on-air transmissions (origination × 
network-TX repeats × relays × relay repeats) reach thousands per second on
three shared 1 Mbps advertising channels. The academic literature confirms
the failure mode: Bluetooth Mesh "is prone to broadcast storm, hindering the
communication reliability for denser deployments" — in simulations of
52/68/86/106-device grids, going denser than ~86 devices *increased* both
loss and delay, and with only 10% of devices generating their own traffic,
end-to-end loss exceeded 10% in denser topologies [S861]. The same study
measured average delay of "around 250 ms for over 10 hops under the worst
simulated network conditions" and showed the protocol "is vulnerable to
external interference" from WLAN despite using only 3 of 40 BLE channels
[S861].

**Vendor-measured scaling (at low rates).** Silicon Labs' Bluetooth Mesh
1.1 performance study — 256 physical nodes (EFR32xG21/xG24) across a
38 m × 19 m office floor plus an 8-box RF-isolation chain for hop tests —
found "latency can be maintained below 200 milliseconds, even out to 6 hops
if the payload is less than 16 bytes" with reliability "greater than 99%"
[S860]. Critically for pewpew, those results were obtained at message
dispatch intervals of 1.5–3 s per sender [S860] — roughly 15–30× slower
than pewpew's per-node rate. There is no vendor evidence for 10 Hz × 50
nodes; the SIG origination bound and the broadcast-storm literature both
predict saturation [S861][S862].

**Provisioning burden.** Every device must be individually provisioned by a
Provisioner before it can participate: it receives the network key (NetKey),
application key(s), and a unique unicast address, over PB-ADV or PB-GATT
with an ECDH key exchange [S863][S864]. ESP-IDF ships a vendor
"fast provisioning" example that can provision "up to 100 devices … in 60
seconds" [S858], but the model remains stateful per-node commissioning —
the opposite of pewpew's join-by-listening, zero-ceremony interop model
(peer fleets speaking fixed-layout broadcasts with no pairing).

**ESP32 support and coexistence.** ESP-BLE-MESH is a first-class ESP-IDF
component, "built on top of Zephyr Bluetooth Mesh stack" and certified
against Mesh Profile v1.0.1, with Mesh Protocol v1.1 features (remote
provisioning, directed forwarding) in examples [S858]. It runs on the same
chips pewpew already targets (ESP32/S3 have BLE 5 radios) — no extra
hardware. But WiFi and BLE share the single 2.4 GHz radio via time-slicing:
Espressif's own coexistence FAQ shows WiFi throughput under BLE-mesh
coexistence collapsing without PSRAM and reaching only ">1 Mbps" with PSRAM
enabled [S859]. Running BLE mesh *and* ESP-NOW-for-interop on one S3 means
two protocol stacks time-sharing one radio next to a 60 fps RMT/LED
workload — RA-16 territory, but the prior is unfavorable [S859].

**License / maintenance.** Spec: open Bluetooth SIG standard (Mesh Protocol
v1.1, 2023) with ongoing SIG maintenance [S864]. ESP implementation:
Apache-2.0 within ESP-IDF, actively maintained by Espressif [S858]. The
technology is stable-to-ascendant in lighting/building automation — but for
*commissioned, low-rate* control traffic, not 10 Hz peer state floods.

### Thread / OpenThread on ESP32-C6/H2

**What it is.** IPv6 mesh (6LoWPAN over IEEE 802.15.4, 250 kbps PHY at
2.4 GHz) with genuine routing, not flooding, for unicast: a self-elected
Leader "aggregates and distributes network-wide configuration information";
"Thread tries to keep the number of Routers between 16 and 23" (hard cap 32
active router IDs), with Router-Eligible End Devices promoted as needed
[S866]. A Border Router's role is to "forward information between a Thread
network and a non-Thread network (for example, Wi-Fi)" and "any device may
serve as a Border Router" [S866] — i.e., a border router is an *egress*
feature; a closed, standalone Thread mesh among peer nodes does not
logically require one, and nodes can be flashed with a shared operational
dataset (network key, PAN ID, channel) so no runtime commissioning ceremony
is needed [S865][NEEDS-VERIFICATION] (confirm pre-shared-dataset join
without a commissioner via an esp-openthread code read — see Open
questions).

**Hardware reality for pewpew.** The ESP32-S3 has no 802.15.4 radio.
Espressif's OpenThread runs natively only "on chips with 15.4 radio such as
ESP32-H2, ESP32-C6 and ESP32-C5"; for S3-class hosts the supported shape is
a Radio Co-Processor: the host "can be connected to an RCP and run
OpenThread under host mode … on Wi-Fi chips such as ESP32, ESP32-S2,
ESP32-S3", over UART or SPI ("For the sake of latency, we recommend using
SPI") [S865]. So Thread for pewpew means either (a) a second radio chip
(C6/H2) on every group node — extra BOM, extra firmware target, extra OTA
path — or (b) moving the group nodes to ESP32-C6 outright (single-core
RISC-V, which then re-opens the render-headroom question RA-16 answers for
the S3). Option (a) buys a dedicated coordination radio that never contends
with the LED-rendering chip's WiFi/ESP-NOW radio — the only candidate in
this survey with that property.

**Scaling and latency evidence.** Silicon Labs' three-way comparison
(AN1142) ran open-air multicast tests at 24/48/96/144/192 nodes: for small
payloads "all three mesh networks [Zigbee, Thread, Bluetooth mesh] provide
very good performance with latency well under 200 milliseconds", Thread
degraded least as payloads grew, and "reliability is generally 99.9% or
better" in multicast tests [S867]. Two heavy caveats transfer to pewpew:
(1) traffic was one multicast every 3 s — the authors note these are
"relatively lightly loaded networks" and that "some network performances
deteriorate further as this multicast load is increased" [S867]; (2)
all-device multicast in Thread is flooding after all: "all-device multicasts
generally flood the network with three re-broadcasts from each router"
[S867]. At pewpew's rates (25–50 originators × 10 Hz), each ~30–50-byte
802.15.4 frame costs ~1.6 ms of airtime on a 250 kbps PHY; 250–500
originations/s plus 3× re-broadcasts from every router node is already
1–2 kframes/s — beyond the channel's ~600 frames/s ceiling for full-size
frames and far beyond it once CSMA back-off is counted. 10 Hz × fleet-wide
state broadcast does not fit a 250 kbps flooding multicast; it could only
work with strong rate discipline (e.g., only-on-change messages) [S867].

**Matter irrelevance.** Matter-over-Thread adds a commissioned,
cluster-based home-automation data model on top of Thread. pewpew's effect
state is a fixed-layout 11-byte peer broadcast with no attributes,
bindings, or fabric membership — Matter adds cost (commissioning, fabric
credentials, certification-shaped stacks) and nothing pewpew needs. Not
pursued further.

**License / maintenance.** OpenThread: BSD-3-Clause, released by Google/Nest,
actively maintained (openthread + esp-openthread port) [S865][S866];
802.15.4/Thread spec stewarded by the Thread Group (spec 1.3.x/1.4 era,
Matter-driven investment) — clearly ascendant as a technology [S866].
Espressif's C6/H2/C5 silicon and IDF support are current and growing
[S865].

### Plain infrastructure WiFi + UDP broadcast via a portable AP/router

**Honest assessment.** This is the boring option: carry a battery-powered
travel router, associate every group node as a plain WiFi station, and let
each node fire its ~11-byte state as a UDP broadcast at 10 Hz. Everything
about it works *except* the premise.

**Loss is a non-issue at this payload/rate.** The tree already established
(RA-04) that WiFi broadcast/multicast frames are sent without ACK or retry,
so loss ≈ raw packet error rate, "not uncommon … 5 percent" [S150]. For
streamed pixels that is disqualifying; for an idempotent 11-byte state
snapshot re-sent every 100 ms it is benign — a lost broadcast costs one
refresh interval of staleness, and expected gap length at 5% i.i.d. loss is
~1.05 intervals. The known caveat is power-save interaction: Espressif's
WiFi driver documents that its AP "doesn't cache the multicast data for the
stations", so "if stations connected to the ESP32 AP are power save enabled,
they may experience multicast packet loss" [S868]; the same DTIM-buffering
behavior on commercial APs adds beacon-interval jitter for broadcast
delivery. Group nodes would run with power save off (they are rendering at
60 fps anyway), which sidesteps this [S868].

**Client-count limits are real at the 150 ceiling.** Theoretical
association limits are generous (Meraki: "128 clients per radio" for Wi-Fi 5
Wave 1, "512 clients per radio" for Wi-Fi 6), but the vendor immediately
qualifies that "in real-world deployment, interference caused by multiple
clients communicating simultaneously will cause this limit to be far lower"
and that the theoretical max "does not mean it is something we want to
design for" [S869]. Enterprise practice recommends ~30 active clients per
AP radio [S870]. 25–50 stations on one consumer/travel AP is plausible when
each sends only ~10 tiny packets/s; 150 stations on one portable AP exceeds
every practical guideline and most consumer firmware limits [S869][S870].
An ESP32 acting as the AP is a non-starter: softAP supports "up to 15
(ESP_WIFI_MAX_CONN_NUM) Wi-Fi connections" (default 10) [S868].

**The structural objections.** (1) The AP *is* infrastructure: a box to
charge, carry, place, and power for the whole event — the requirement this
tier exists to eliminate. (2) Single point of failure: AP dies → the whole
fleet is instantly deaf, vs. graceful per-node degradation in any peer
scheme. (3) Association is stateful: nodes at the RF fringe flap between
associated/disassociated and take seconds to rejoin, versus connectionless
broadcast where fringe nodes just hear fewer packets. (4) Range is set by
the *AP's* placement and antenna, not by node-to-node adjacency — no
multi-hop extension at the far end of a deployment. None of these are
performance claims requiring measurement; they are consequences of the
architecture [S869][S150].

**License / maintenance.** Not applicable (standard 802.11 + BSD sockets);
the "maintenance status" of this option is that of the router purchased.
Stable by definition.

### 802.11 LR (Espressif Long Range mode)

**What it is.** "Long Range (LR) mode is an Espressif-patented Wi-Fi mode
which can achieve a one-kilometer line of sight range" [S868]. It is a
proprietary PHY: "only ESP32 devices can transmit and receive the LR data"
[S868]. Raw PHY rates are 0.25/0.5 Mbps ("The raw PHY data rates is 1/2
Mbps and 1/4 Mbps"), receiver sensitivity gains "about 4 dB … than the
traditional 802.11B mode, theoretically the transmission distance is about
2 to 2.5 times the distance of 11B" [S868]. Espressif recommends it when
"both the AP and station are Espressif devices", links must be long, and
"data throughput requirements are very small, such as remote device
control" [S868] — a description that matches pewpew's state traffic
exactly.

**How it composes with the other candidates.** LR is not a transport; it is
a PHY mode underneath one. A mixed 802.11BGN+LR protocol mode lets
Espressif APs serve both normal and LR clients [S868]. Critically for
pewpew, the PHY rate table in ESP-IDF exposes LR rates to ESP-NOW-style
traffic: `WIFI_PHY_RATE_LORA_250K` / `WIFI_PHY_RATE_LORA_500K`, documented
in the IDF headers as "Espressif-specific Long Range mode rate"
[S872:components/esp_wifi/include/esp_wifi_types_generic.h#L1236-L1237],
and ESP-NOW supports per-peer rate configuration via
`esp_now_set_peer_rate_config()` [S871]. So the realistic role of LR in
pewpew is **an option flag on the RA-13 ESP-NOW design** — trade 4× airtime
per frame (1 Mbps default → 0.25 Mbps) for ~4 dB link margin on sparse,
far-flung deployments — not a competing transport. Airtime math: an
ESP-NOW state frame of ~40 bytes over-the-air costs ~1.3 ms at 250 kbps;
150 nodes × 10 Hz × 1.3 ms ≈ 2.0 s/s — over channel capacity, so LR at the
full design ceiling and full rate does not fit; at 25–50 nodes (0.3–0.65 s/s
before contention) it is workable but tight [S868][S872].

**Vendor lock and verdict-relevant caveats.** LR locks the radio tier to
Espressif silicon permanently (acceptable — the interop constraint already
assumes ESP-NOW peers, which is equally Espressif-locked), and LR frames
are invisible to standard WiFi sniffers, complicating debugging. Espressif
maintains LR across chip generations (present in ESP32 through
S3/C-series-era docs and current IDF headers) [S868][S872]. Stable,
niche, vendor-proprietary.

### LoRa / LoRaWAN (brief — out-of-family)

Disqualified in one paragraph. LoRa's regional regulatory regime caps
airtime: under ETSI EN 300 220 the common 868 MHz sub-bands allow 0.1–1%
duty cycle (10% only in 869.4–869.65 MHz) [S873]. A device that transmits
10 times per second at even ~40 ms airtime per small SF7BW125 frame is at
~40% duty cycle — 40–400× over the legal budget in the EU bands, and The
Things Network's own docs state the general truth: LoRaWAN is unsuitable
for "Realtime data — you can only send small packets every couple of
minutes", with LoRa bitrates of "between 250bit/s and 11kbit/s in Europe"
[S874]. Even ignoring regulation (e.g., US 915 MHz dwell-time rules), a
shared LoRa channel offers ≤11 kbit/s while 25–50 nodes × 10 Hz × ~30-byte
frames require ≥60–120 kbit/s of goodput — the channel is over-subscribed
several times before collisions are counted [S874]. LoRa remains
interesting for pewpew only as a possible sub-1 Hz out-of-band "show
control / are-you-alive" side channel at multi-km range — a different
problem than this document's. Not a candidate for 10 Hz state.

### Comparison table

Baseline for comparison: ESP-NOW broadcast (RA-13) — connectionless,
single-hop flooding at 1 Mbps+ on ESP32-class radios, zero infrastructure,
zero commissioning, MIT-licensable via IDF (Apache-2.0), maintained by
Espressif.

| Transport | Realistic node ceiling (evidence) | Latency for group state | Infra needed | License | Maintenance (2026) | Verdict for pewpew |
|---|---|---|---|---|---|---|
| painlessMesh | ~30–40 stable; degrades 50+, fails ~72 [S851][S852] | multi-hop TCP tree + JSON parse; unbounded under load [S850] | none | GPL-3.0 [S850] | v1.5.7 2025-10, slow upstream; active fork unadopted [S850][S856] | **Disqualified** — ceiling inside target range; GPLv3; waning |
| ESP-WIFI-MESH | 100 vendor-tested; 512–1000 claimed [S853][S854] | 10–30 ms/hop; ≤6 layers ⇒ ≲300 ms leaf-to-leaf [S853] | none, but no-router mode has fixed root = SPOF [S854] | Apache-2.0 (ESP-IDF) | maintained, but vendor steers new designs to Mesh-Lite [S854] | **Disqualified** — root SPOF without router; superseded by vendor |
| ESP-MESH-LITE | 50 vendor-tested [S855] | 8–12 ms/hop, but 45–50 s self-heal [S855] | none, but fixed root in no-router mode [S855][S854] | Apache-2.0 text, closed-source core blobs [S855] | active, Espressif-recommended [S854] | **Disqualified** — no mesh-wide broadcast (NAT subnets), root SPOF, binary blob |
| BLE Mesh | 256 measured at ≤0.7 msg/s/node [S860]; broadcast-storm-prone ≥86 dense nodes [S861] | <200 ms to 6 hops (small payloads, light load) [S860] | provisioner required per node [S863] | SIG spec open; ESP impl Apache-2.0 [S858] | active (SIG + Espressif) [S858][S864] | **Disqualified at 10 Hz** — spec caps origination at 10 msg/s/node before relays [S862]; flood saturates 3 adv channels |
| Thread (C6/H2) | 192 measured at 0.33 multicast/s [S867]; 250-device subnets typical [S866] | <200 ms multicast, light load [S867] | none (BR only for egress) [S866] | OpenThread BSD-3 [S865] | ascendant (Matter-driven) [S865][S866] | **Disqualified as-specified** — 250 kbps PHY can't carry 10 Hz fleet-wide flood [S867]; needs 2nd radio chip next to S3 [S865] |
| WiFi AP + UDP broadcast | 25–50 practical/AP radio; ~150 exceeds practice [S869][S870] | one hop, ms-class; 5% benign loss at 10 Hz refresh [S150] | **portable AP — violates zero-infra**; SPOF | n/a (standard) | n/a | **Disqualified by requirement**, not by physics — viable fallback where an AP is acceptable |
| 802.11 LR | = ESP-NOW fleet at ¼ airtime budget: OK 25–50, over budget at 150 × 10 Hz [S868][S872] | single hop, ms-class | none | Espressif-proprietary PHY [S868] | maintained in IDF [S872] | **Viable as an ESP-NOW option flag** (RA-13), not a separate transport |
| LoRa/LoRaWAN | n/a at 10 Hz (duty cycle 0.1–1%) [S873] | seconds–minutes between legal TX [S874] | none (LoRa) / gateway (LoRaWAN) | LoRa PHY proprietary Semtech; LoRaWAN spec open | active | **Disqualified** — 2–3 orders of magnitude short on rate; possible <1 Hz side channel only |

**Recommendation frame.** For 25–50 zero-infrastructure groups exchanging
~11-byte state at ~10 Hz, exactly one family survives this survey:
single-hop connectionless broadcast on the WiFi PHY — i.e., ESP-NOW
(RA-13), optionally at the LR PHY rate for sparse long-range layouts
[S868][S871][S872]. Every mesh candidate fails for a structural reason,
not a tuning reason: the softAP+STA trees (painlessMesh, ESP-WIFI-MESH,
ESP-MESH-LITE) trade pewpew's flat, loss-tolerant broadcast for stateful
topology with roots, healing times, and (routerless) single points of
failure [S851][S853][S854][S855]; the flooding meshes (BLE Mesh, Thread
multicast) have vendor-measured scaling evidence only at per-node rates
15–30× below pewpew's, and saturate their narrow channels at 10 Hz ×
25–150 originators [S860][S861][S862][S867]. If the zero-infrastructure
constraint is ever relaxed (a permitted base station), plain WiFi + UDP
broadcast is the honest second choice — boring, lossy-but-tolerably-so,
and protocol-compatible with the host-engine tier [S150][S869]. If
multi-hop range extension ever becomes a hard requirement beyond what LR
buys, Thread-on-C6-companion is the least-bad mesh — the only candidate
whose radio does not contend with the render chip's — but only with
on-change (not fixed 10 Hz) message discipline [S865][S867].

## Verdicts

- **painlessMesh — waning.** Upstream alive but minimal (v1.5.7 2025-10-01,
  small maintainer group) [S850]; field reports show collapse at 50–72 nodes
  [S851][S852]; GPLv3 [S850]; JSON-over-TCP design is CPU-hostile to a 60 fps
  render loop [S850]. Do not build on it.
- **ESP-WIFI-MESH — stable but vendor-superseded (waning for new designs).**
  Maintained in ESP-IDF, 100-node vendor test [S853], but Espressif itself
  says new work should use Mesh-Lite [S854], and routerless operation has an
  unrecoverable fixed-root SPOF [S854].
- **ESP-MESH-LITE — ascendant within its niche, wrong niche.** Actively
  developed, Espressif-recommended [S854][S855]; but closed-source core
  blobs, 45–50 s heal times, NAT-partitioned subnets with no mesh-wide
  broadcast, and a fixed root in no-router mode [S855].
- **BLE Mesh — stable technology, disqualified workload.** SIG + Espressif
  actively maintain it [S858][S864]; scaling evidence (256 nodes) exists only
  at ≤0.7 msg/s per node [S860]; the spec's own origination bound (≤10
  msg/s/node) is met exactly by pewpew's heartbeat before any relaying, and
  flooding literature predicts broadcast storm at pewpew's density and rate
  [S861][S862].
- **Thread/OpenThread — ascendant technology, mismatched PHY and BOM.**
  BSD-3, Matter-funded, healthy [S865][S866]; 192-node multicast measured
  at light load [S867]; but 250 kbps 802.15.4 cannot carry 10 Hz fleet-wide
  floods, and ESP32-S3 needs a C6/H2 companion radio to speak it at all
  [S865][S867].
- **Infrastructure WiFi + UDP broadcast — stable, disqualified by
  requirement.** Works at 25–50 stations with benign 5%-class loss for
  periodic tiny state [S150][S869]; the AP is exactly the infrastructure and
  SPOF this tier forbids; ~150 stations exceeds practical AP guidance
  [S869][S870].
- **802.11 LR — stable, proprietary, and useful only as a modifier.** Not a
  transport; an Espressif-only PHY rate that ESP-NOW can adopt per-peer for
  ~4 dB more link margin at 4× airtime [S868][S871][S872]. Keep as an RA-13
  design option, with the interop caveat recorded in Open questions.
- **LoRa/LoRaWAN — healthy ecosystem, physically disqualified at 10 Hz.**
  Duty-cycle law and ≤11 kbit/s rates put it 2–3 orders of magnitude short
  [S873][S874]; candidate only for a future sub-1 Hz long-range side
  channel.

**Bottom line:** nothing in this survey displaces ESP-NOW broadcast (RA-13)
for the stated workload. The alternatives partition cleanly into
requirement violations (portable AP), structural mismatches (all three
softAP+STA trees; provisioned flooding meshes at 10 Hz), PHY-rate walls
(Thread, LoRa), and one composable option (LR PHY under ESP-NOW).

## Code-reading queue

1. **espressif/esp-idf — ESP-NOW rate path** (`components/esp_wifi`,
   esp_now_set_peer_rate_config → LR rates): confirm broadcast-peer frames
   can be sent at `WIFI_PHY_RATE_LORA_250K` and what receivers must
   configure to hear them [S872]. Feeds the RA-13 LR option and its interop
   caveat. (High — only item that changes a live design decision.)
2. **espressif/esp-mesh-lite — communication API semantics**
   (`components/mesh_lite/include/esp_mesh_lite_core.h`, comm socket layer):
   does any primitive deliver one message to *all* nodes, at what fan-out
   cost, and how does it behave during the 45–50 s heal window? [S855]
   (Medium — closes the "no mesh-wide broadcast" finding rigorously.)
3. **espressif/esp-openthread — dataset-only join**: verify a node flashed
   with a pre-shared operational dataset joins/forms a network with no
   commissioner, and measure C6 join time after power-loss churn [S865].
   (Medium — only matters if multi-hop range extension becomes a
   requirement.)
4. **painlessMesh — sub-connections buffer + broadcast path**
   (`src/painlessmesh/router.hpp`, `connection.hpp` at pin
   [S850]): understand the actual scaling failure mode (topology-JSON
   growth vs TCP buffer exhaustion) so the disqualification is mechanistic,
   not anecdotal. (Low — forensic interest only.)

## Open questions

- **No candidate has published evidence at pewpew's actual operating point**
  (25–50 originators × 10 Hz). BLE Mesh and Thread vendor tests run at
  0.3–0.7 msg/s per sender [S860][S867]; the saturation arguments above are
  arithmetic, not measurement. A 25-node ESP-NOW-vs-BLE-mesh bench at 10 Hz
  would settle it, but only if the ESP-NOW baseline (RA-13) looks shaky —
  otherwise not worth the fixture cost.
- **802.11 LR breaks the interop constraint as stated.** Peer fleets
  broadcast ESP-NOW at the standard 1 Mbps rate; LR frames use a different
  PHY that standard-rate receivers cannot decode [S868]. Is mixed-mode
  reception (BGN+LR protocol mask on receivers) sufficient for a node to
  hear *both* LR fleet traffic and standard-rate peer-fleet traffic
  simultaneously? Needs a two-node bench test; determines whether LR is a
  fleet-wide toggle or forbidden while interop is active.
- **Exact BLE mesh unsegmented payload split** (11-octet access payload =
  opcode + params) is cited here via TI's stack guide [S863]; verify against
  MshPRT v1.1 §lower-transport tables [S864] before any ADR relies on the
  "11 bytes fits/doesn't fit" boundary.
- **Thread join-without-commissioner** (pre-shared operational dataset at
  flash time) is asserted from API shape, tagged NEEDS-VERIFICATION in
  Findings; settle via esp-openthread code read or 3-node bench [S865].
- **painlessMesh scaling reports are ESP8266-era** [S851][S852]; an
  ESP32-S3 fleet would fare somewhat better (more heap, second core), but
  no published S3-class painlessMesh scaling data was found, and the
  GPLv3 + maintenance verdicts stand regardless.
- **Portable-router firmware client caps** (typical travel-router
  max-station limits, e.g. GL.iNet-class hardware) were not verified against
  vendor spec sheets; only enterprise-AP guidance is cited [S869][S870]. If
  the AP fallback is ever pursued, check the specific router's station limit
  and 2.4 GHz airtime behavior at 50 stations.
- **ESP-MESH-LITE node-capacity ceiling**: Espressif publishes topology
  limits (15 layers × 10 downstream) and a 50-device test [S855] but no
  hard maximum; whether 150 nodes is realistic on Mesh-Lite is unknown —
  moot unless the root-SPOF and broadcast findings are overturned.
