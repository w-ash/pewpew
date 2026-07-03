# RA-04: Protocols & transport

Last researched: 2026-07-03
Status: draft
S-ID block: S150–S199

## Key questions

- Which pixel transport protocols suit a Python-host -> network-receiver architecture?
- DDP: header overhead, 1440 channels/packet, native 16-bit wire format, sync semantics, implementers.
- sACN/E1.31: universe model, 512-channel limit, multicast vs unicast at scale, sync packets, priority.
- Art-Net 4: ArtSync, capabilities vs sACN.
- OPC (legacy status).
- WLED's own UDP realtime + sync protocols (DNRGB etc.).
- FPP MultiSync.
- Packets-per-frame math: 500/2000/10000 RGB pixels @ 60fps, 8-bit and 16-bit, per protocol.
- WiFi realities on ESP32 receivers (jitter, loss, receivers per AP); Ethernet options.
- Latency/jitter budgets practitioners measure.
- Which protocol should a quality-focused Python engine speak natively?

## Findings

### DDP (Distributed Display Protocol)

Open spec by Mark Lottor / 3waylabs, "may be freely used and implemented by anyone"; last spec update 2022-09-05; UDP (optionally TCP) on port 4048 [S150].

**Wire format.** Single 10-byte header for all packets (14 bytes when the Timecode flag is set), followed by data [S150]:
- byte 0: flags — 2-bit version (v1 = `01`), T (timecode appended), S (data from local Storage), R (Reply), Q (Query), P (Push).
- byte 1: 4-bit sequence number 1–15 (0 = unused); receivers may drop back-to-back duplicates; senders may repeat packets with the same sequence for redundancy.
- byte 2: data type — `C R TTT SSS` where TTT ∈ {undefined, RGB, HSL, RGBW, grayscale} and SSS = bits per pixel *element* ∈ {1, 4, 8, 16, 24, 32}. **16 bits/channel is a first-class wire format** (type byte RGB+16 = `0b00001100`); no other mainstream pixel transport has this [S150].
- byte 3: destination ID (1 = default output; 246/250/251 = JSON control/config/status; 254 = DMX transit; 255 = all).
- bytes 4–7: 32-bit data offset (bytes, MSB-first) into the receiver's frame buffer — so a frame is assembled from arbitrarily-ordered blocks, and partial updates (only changed bytes) are legal because the buffer persists between frames [S150].
- bytes 8–9: 16-bit data length. Reference `DDP_MAX_DATALEN` is 480×3 = **1440 bytes** ("fits nicely in an ethernet packet" — 1440 + 10 DDP + 8 UDP + 20 IP = 1478 < 1500 MTU) [S150].

**Sync semantics.** Two optional mechanisms [S150]:
1. **Push flag**: a device displays its buffer immediately on receiving P. Single device: set P on the last data packet of the frame. Multiple devices: fill all buffers, then broadcast a 10-byte data-less P packet so all devices flip simultaneously — usable "when all display devices are on a single network that supports broadcasts and latency is minimal".
2. **Timecode**: T+P with a 4-byte timecode (middle 32 bits of 64-bit NTP time: 16-bit seconds + 16-bit fraction, 15 µs resolution) telling the display *when* to push; requires NTP-synced receivers. Late data still goes into the buffer; display-or-drop is receiver policy.

**Efficiency (spec's own math).** Counting 66 bytes Ethernet + 20 IP + 8 UDP overhead: E1.31 = 512/(66+126+512) = 72.7% efficient; Art-Net = 85.9%; DDP = 1440/(66+10+1440) = 94.9%. Max RGB pixels addressable at 45 fps on 100 Mbit: E1.31 67,340; Art-Net 79,542; DDP 87,950 [S150].

**Extras.** Query/Reply for reading buffers and JSON status/config; broadcast discovery via JSON-status query (replies staggered by last MAC byte, controller waits ~500 ms); DMX legacy transit ID with universe in the offset field; storage-playback flag. Security: none — assumes private lighting network [S150]. The spec explicitly cites Cisco's WLAN white paper on why it avoids multicast: WiFi multicast has no retransmission, so multicast loss ≈ raw PER, "not uncommon ... 5 percent", vs <0.1% for retried unicast [S150].

**Who implements it.** WLED accepts DDP as a realtime stream since 0.11.0 (Nov 2020) and can send DDP from 0.13 [S153][S152]; WLED-MM recommends DDP for WLED-to-WLED virtual-LED setups (up to 1440 channels/packet vs Art-Net's 512) but notes Art-Net has "a MUCH wider adoption" [S152]. xLights supports DDP as a controller output [S154]. Falcon Player (FPP) supports DDP output [S155]. LedFx (Python) transmits DDP as its preferred device type [S156]. Minleon NDB/WiFi controllers are the original commercial implementation [S150]. The xLights manual lists DDP support on "FPP/Kulp, HinksPix, Falcon v3/v4/v5, WLED, Genius, and Minleon" controllers and calls it "more efficient than ArtNET or E.131" [S164].

**Limitations honestly stated.** Parts of the spec (some JSON schema, storage semantics) are marked "not decided upon or standardized" [S150]. There is no per-universe priority/arbitration like sACN's, no built-in merging of multiple senders, and destination-ID semantics beyond ID 1 are loosely defined [S150]. Maintenance: spec is frozen-stable (last touched 2022-09-05); ecosystem adoption still growing via WLED/xLights/FPP/LedFx [S150][S152][S154].

### sACN / E1.31 (Streaming ACN)

ANSI standard (E1.31-2016, superseded by E1.31-2018) from ESTA; free PDF; the entertainment industry's DMX-over-IP standard [S157].

**Universe model.** A universe = up to 512 data slots (octets); universe numbers 1–63999 (64214 reserved for discovery) [S157]. RGB pixels get 170 per universe (510 of 512 slots used) — a large pixel install becomes dozens-to-hundreds of universes that the sender must map, and each universe is a separate 638-byte packet: **126 bytes of layered overhead** (ACN root layer + E1.31 framing layer + DMP layer, octets 0–125) before the 513-byte property values (START code + 512 slots) [S157]. DDP's spec computes the resulting efficiency at 72.7% vs DDP's 94.9% [S150].

**Priority & multi-source arbitration** — sACN's unique strength. Every data packet carries a priority 0–200 (default 100); receivers take the highest-priority active source, and the standard defines sources-exceeded and merge/arbitration requirements (HTP merge etc. are receiver policy) [S157]. This enables console + effects-engine coexistence on one rig — nothing in DDP/Art-Net/OPC matches it. A source is considered lost after `E131_NETWORK_DATA_LOSS_TIMEOUT` = **2.5 s** without packets or on a Stream_Terminated option bit [S157].

**Multicast vs unicast.** Universe N maps to multicast group 239.255.<hi>.<lo> (e.g. universe 1 → 239.255.0.1); receivers IGMP-join only the universes they patch. Unicast is explicitly permitted but has no discovery mechanism [S157]. At scale on wired networks with IGMP-snooping switches, multicast lets one transmit serve many listeners; on WiFi, multicast frames are sent without ACK/retry at low basic rates, so loss ≈ raw PER (up to ~5%) versus <0.1% for retried unicast [S150] — practitioners running WiFi receivers (WLED) are consistently steered to unicast [S158].

**Sync packets.** E1.31-2016 added universe synchronization: data packets carry a 2-byte Synchronization Address (a universe number on which sync packets are sent); receivers holding data then latch on receipt of an E1.31 Synchronization Packet on that address; a Force_Synchronization option bit controls behavior if sync is lost, and receivers drop back to unsynchronized display if no sync packet arrives within 2.5 s [S157]. The spec itself recommends sources "introduce a configurable delay between data packets and the subsequent transmission of the E1.31 Synchronization Packet" to let receivers finish processing — i.e., even the standard acknowledges receiver-side processing jitter [S157]. Universe discovery packets (every 10 s on universe 64214) enumerate active universes [S157].

**Sequence numbers** are full 8-bit per universe (vs DDP's 4-bit), letting receivers detect out-of-order/duplicate packets [S157].

**Bit depth.** Slots are 8-bit only. 16-bit control requires ad-hoc coarse/fine slot pairs (a DMX convention for moving heads, not standardized for pixel data); no pixel receiver ecosystem (WLED, Falcon, etc.) consumes 16-bit pixel data over sACN [S157][S150].

**Maintenance/status.** ANSI-maintained, current edition 2018-11-07 [S157]; universally implemented (consoles, xLights, FPP, WLED, ESPixelStick, every commercial pixel controller). Stable/entrenched, but the 512-slot universe model is a legacy-DMX artifact that costs packet efficiency and forces universe bookkeeping onto the sender [S150][S157].

### Art-Net 4

Proprietary-but-royalty-free protocol by Artistic Licence ("Any third parties are welcome to use this communication protocol without royalty"; © Artistic Licence 1998–2025; trademark credit required); current release Art-Net 4 Protocol Release V1.4, document revision 1.4dp dated 2025-10-23 — actively maintained [S159].

**Wire format.** ArtDmx = 18-byte header ("Art-Net\0" ID, opcode, protocol version, sequence, physical port, 15-bit Port-Address, length) + up to 512 bytes DMX data = 530 bytes max [S159]. Sequence field is 8-bit (0x01–0xff; 0x00 disables) explicitly for re-ordering "when Art-Net is carried over a medium such as the Internet" [S159].

**Addressing.** 15-bit Port-Address = 7-bit Net + 4-bit Sub-Net + 4-bit Universe = 32,768 theoretical universes; the spec's own rule-of-thumb caps *practical* unicast at 40 universes on 10BaseT, 400 on 100BaseT, "4000+" on gigabit [S159].

**Unicast mandated.** Art-Net 4 requires ArtDmx be unicast to subscribers discovered via ArtPoll/ArtPollReply: "There are no conditions in which broadcast is allowed" for ArtDmx (a change from the broadcast-everything Art-Net 1/2 era) [S159].

**ArtSync.** "A controller that wishes to implement synchronous transmission will unicast multiple universes of ArtDmx and then broadcast an ArtSync to synchronously transfer all the ArtDmx packets to the nodes' outputs at the same time." Nodes power up non-synchronous (display on receipt), switch to synchronous (buffer until next ArtSync) on first ArtSync, and time out back to non-synchronous after 4 s without one [S159]. Functionally equivalent to DDP's broadcast-Push.

**vs sACN.** No standardized priority field on ArtDmx (merging is node policy; ArtPollReply reports merge mode); richer device-management side (ArtAddress remote programming, ArtIpProg, RDM transport, firmware upload, timecode/trigger packets) [S159]. DMX512 gateways cap at 44 Hz refresh but "non-DMX512 gateways can declare a higher framerate limit" via ArtPollReply-RefreshRate [S159]. Like sACN, payload slots are 8-bit only; 16-bit needs coarse/fine pairs. Efficiency 85.9% by DDP's math (18-byte header, no ACN layering) — better than sACN, worse than DDP [S150].

**Status.** Stable/entrenched; the most widely implemented pixel/DMX-over-IP protocol (consoles, media servers, WLED, xLights, FPP, Resolume, TouchDesigner) [S152][S159].

### OPC (Open Pixel Control)

Minimal TCP protocol by Micah Scott / Ka-Ping Yee, designed for the FadeCandy controller: 4-byte header (channel, command, 2-byte length) + up to 65535 bytes of 8-bit RGB data; channel 0 = broadcast; command 0 = set-8-bit-pixels; a sysex-style command range exists, and 16-bit color existed only as a FadeCandy-specific extension, not a standard message [S160]. TCP framing means head-of-line blocking on loss — a stale frame is retransmitted rather than dropped, the opposite of what realtime pixel streaming wants [S160]. **Legacy/waning**: FadeCandy hardware was discontinued and the repo archived by its owner on 2023-05-09 (read-only) [S161]; OPC survives mainly in art-project code (Open Pixel Control server implementations, LedFx retains an OPC output) but no active spec development since ~2013 [S160][S161]. Not a candidate for new architecture.

### WLED native UDP realtime + sync

**Realtime protocols** (default UDP port 21324, configurable; byte 0 = protocol ID, byte 1 = timeout in seconds before WLED resumes normal effects, 255 = never) [S162]:
- **WARLS** (protocol 1): indexed — 4 bytes/LED (index,R,G,B), max 255 LEDs; good for sparse updates.
- **DRGB** (protocol 2): sequential RGB, 3 bytes/LED, max 490 LEDs — one packet only, no offset.
- **DRGBW** (protocol 3): sequential RGBW, 4 bytes/LED, max 367 LEDs.
- **DNRGB** (protocol 4): sequential RGB with a 2-byte start-index header, 489 LEDs/packet — the only WLED-native mode that scales past one packet, effectively a poor-man's DDP offset field [S162].

Individual LEDs hold their last value until changed or timeout; partial updates supported [S162]. No push/sync flag, no sequence numbers, no bit depth other than 8-bit, no discovery — strictly a WLED-ecosystem convenience. WLED itself also receives DDP, E1.31, Art-Net, and Hyperion protocols, and since 0.13 can forward/send DDP [S158][S153]; the WLED-MM docs recommend DDP over the native modes for WLED-to-WLED streaming [S152].

**WLED UDP sync notifier** (ports 21324/65506-region, "UDP sync") is a *state*-sync protocol — it broadcasts preset/effect/brightness changes so groups of WLED devices mirror each other; it is not a pixel-streaming transport and carries no per-pixel data [S158]. Useful context: it is how multi-device WLED installs stay coherent *without* a central engine, i.e., the architecture pewpew replaces.

**Status.** WLED native realtime modes: stable but frozen legacy (docs unchanged for years; DDP is the recommended path for new senders) [S152][S162].

### FPP MultiSync

Falcon Player's player-to-player synchronization protocol — **not a pixel transport**. UDP port 32320, multicast 239.70.80.80 ("239.F.P.P"); packets start `'F','P','P','D'` + type + length [S163]. The MultiSync packet (type 0x01) carries a sync action (Start/Stop/Sync/Open), a sync type (FSEQ sequence file vs media file), a 4-byte frame number, a float seconds-elapsed, and the filename [S163]. A master periodically (≈1/s or faster) tells remotes what frame of a locally-stored .fseq file it is playing; each remote plays its own copy and slews to stay within ±1 frame [S155][S163]. Ping/Discover packets (type 0x04) carry hardware ID, version, mode, and channel ranges; a Blank Data packet (0x03) blanks output [S163].

**Relevance to pewpew**: MultiSync is the "distribute content ahead of time, sync playback pointers" architecture — the alternative to streaming pixels in real time. It scales to huge shows on weak networks because only tiny sync packets cross the wire, but it cannot do live/generative content, which is pewpew's whole premise. Useful as a fallback pattern if pre-rendered sequences are ever supported. Status: actively maintained (FPP releases ongoing, 2025+) [S155][S163].

### Packets-per-frame math

Computed from the cited packet formats (payload capacities: DDP 1440 B [S150]; sACN 510 B used of 512 = 170 RGB px, 638 B on wire [S157]; Art-Net 510 B used = 170 RGB px, 528 B on wire [S159]; WLED DNRGB 489 px [S162]). RGB = 3 B/px at 8-bit, 6 B/px at 16-bit. Pixel-aligned packing (DDP: 480 px/packet at 8-bit, 240 px at 16-bit).

**Packets per frame (and per second at 60 fps):**

| Protocol | depth | 500 px | 2000 px | 10000 px |
|---|---|---|---|---|
| DDP | 8-bit | 2 (120/s) | 5 (300/s) | 21 (1260/s) |
| DDP | 16-bit | 3 (180/s) | 9 (540/s) | 42 (2520/s) |
| sACN | 8-bit | 3 (180/s) | 12 (720/s) | 59 (3540/s) |
| sACN | 16-bit* | 6 (360/s) | 24 (1440/s) | 118 (7080/s) |
| Art-Net | 8-bit | 3 (180/s) | 12 (720/s) | 59 (3540/s) |
| Art-Net | 16-bit* | 6 (360/s) | 24 (1440/s) | 118 (7080/s) |
| WLED DNRGB | 8-bit | 2 (120/s) | 5 (300/s) | 21 (1260/s) |
| OPC (TCP) | 8-bit | 1 msg (~2 TCP segs) | 1 msg (~5 segs) | 1 msg (~21 segs) |

\* Not a standard wire format for sACN/Art-Net — assumes ad-hoc coarse/fine slot pairs (85 px/universe), which no mainstream pixel receiver implements [S157][S159]. Only DDP carries 16-bit natively [S150]. Add +1 broadcast sync packet per frame for DDP Push, sACN sync, or ArtSync when frame-coherent output across devices is wanted [S150][S157][S159]. WLED DNRGB has no 16-bit and no sync.

**Approximate wire bandwidth at 60 fps, 10000 px** (payload + protocol header + 66 B Ethernet/IP/UDP overhead per packet, per DDP's accounting [S150]):
- DDP 8-bit: (30000 + 21×76) B/frame ≈ 15.2 Mbit/s; 16-bit ≈ 30.3 Mbit/s.
- sACN 8-bit: 59 × (638+66) ≈ 19.9 Mbit/s.
- Art-Net 8-bit: 59 × (528+66) ≈ 16.8 Mbit/s.

Takeaways: (1) at every scale sACN/Art-Net need ~2.8× the packets of DDP because the universe abstraction wastes packet capacity; per-packet interrupt/processing cost, not raw bandwidth, is what saturates small receivers [S150][S152]. (2) 16-bit doubles everything; only DDP expresses it without inventing a convention. (3) Even the worst case (sACN 16-bit hack, 10000 px) is ~40 Mbit/s — trivial for gigabit Ethernet hosts, but 3540+ pps at the receiver side is far past a single ESP32's comfortable ingest (see WiFi section); 10000-pixel rigs are multi-receiver by necessity, so per-receiver rates are what matter.

### WiFi realities on ESP32 receivers

**Measured latency/jitter.** Electric UI's 2024 logic-analyzer benchmark (two ESP32s via a Unifi U6+ AP at ~5 m): with default ESP-IDF config, medians were a dismal 74–84 ms; after disabling modem power-save, disabling Nagle, and putting WiFi/LwIP stacks in IRAM, TCP medians hit ~6 ms and UDP ~9 ms with worst-case outliers ~25 ms [S166]. Espressif's own issue tracker documents a "long tail of jitter" in ESP32 UDP send timing tied to FreeRTOS scheduling, with receive-timestamp jitter in the tens of ms [S167]. In noisy RF environments, forum-measured UDP delays reach 200–388 ms [S168][NEEDS-VERIFICATION]. Modem sleep is the single biggest lever: WLED's docs tell users "disabling WiFi sleep ... can reduce/eliminate visual stuttering/lag" and yields sub-10 ms ping on ESP32 [S158][S167].

**Throughput/receiver limits.** WLED's FAQ: 750 LEDs is "the recommended maximum" per controller; 1000 LEDs at 30 fps needs ~720 kbit/s, "difficult to achieve with most cheap ESP boards over WiFi"; "your WiFi network could become the limiting factor quickly"; external antenna boards "significantly better" than PCB-antenna boards [S165]. For sACN specifically WLED recommends ≤3 universes (510 px) for a smooth 40 fps [S158]. Per-packet processing cost matters more than bandwidth on these receivers — a rationale for DDP's fewer, fuller packets: WLED's FAQ recommends DDP because "the reduced overhead" improves "the fluidity of your animations" [S165].

**Receivers per AP.** No authoritative per-AP device count surfaced; practitioner guidance is qualitative — dedicated show SSID/AP, 2.4 GHz-only ESP32s share airtime, and each added realtime stream multiplies airtime use; the xLights/FPP community norm is to hard-wire the sender and use FPP instances as WiFi→Ethernet proxies for distant controllers rather than streaming to many WiFi endpoints [S164][S165]. Open question below.

**Multicast on WiFi** is effectively unusable for realtime pixels: no L2 retransmission, loss ≈ raw PER (~5% not uncommon per Cisco), and APs transmit multicast at low basic rates [S150]. Unicast per receiver is the practitioner default [S158][S150].

### Ethernet options

WLED's FAQ: "the best way to ensure a low-latency, reliable, fluid stream when using large quantities of LEDs is to invest in a wired Ethernet ESP32 board like QuinLED-Dig boards with ethernet or the Olimex ESP32-POE" [S165]. Classic ESP32 (not S3/C3) has an on-die Ethernet MAC needing only an external RMII PHY (LAN8720); common boards: Olimex ESP32-POE(-ISO), WT32-ETH01, QuinLED-Dig-Uno/Octa Ethernet variants [S165][S158]. Larger installs use commercial pixel controllers (Falcon, Kulp, HinksPix, Genius) that are Ethernet-native and speak DDP/E1.31/Art-Net [S164]. WLED-MM likewise states Ethernet gives "superior stability" vs WiFi for network LED control [S152]. For pewpew's room-scale tier, Ethernet receivers are the quality path; WiFi is the convenience/wearable path with a real jitter tax [S165][S166].

### Latency/jitter budgets

- Frame budget at 60 fps is 16.7 ms; delivery jitter beyond one frame period shows as judder. Optimized ESP32 WiFi (~9 ms median, ~25 ms outliers [S166]) therefore sits right at the edge: median fits, tail causes occasional dropped/late frames — acceptable if receivers display latest-data (UDP semantics) rather than blocking (TCP/OPC).
- E1.31's own spec acknowledges receiver-side processing jitter, recommending senders delay sync packets after data "in environments with high latency or low bandwidth ... to mitigate some of the perceptible jitter" [S157].
- Source-loss watchdogs define the outage budget: sACN 2.5 s [S157], Art-Net sync-mode timeout 4 s [S159], WLED realtime timeout is sender-set in seconds [S162]. These are blackout-fallback thresholds, not smoothness budgets.
- For music-synchronized effects, end-to-end (audio → light) alignment within ~10 ms is the perceptual bar commonly cited for AV sync tightness; WiFi's tail jitter alone can exceed it, so audio-reactive quality argues for Ethernet receivers or receiver-side buffering with timecoded display (DDP T-flag with NTP, 15 µs resolution [S150]) [S166][NEEDS-VERIFICATION on the 10 ms perceptual figure — RA-10's territory].

## Verdicts

- **DDP — ascendant.** Spec frozen-stable since 2022, but adoption keeps widening (WLED 0.11+, WLED-MM's recommended WLED-to-WLED transport, xLights, FPP/Kulp, Falcon, HinksPix, Genius, Minleon, LedFx) [S150][S152][S164][S156]. Best efficiency (94.9%), only native 16-bit wire format, simplest header, offset-based partial updates, broadcast-Push and NTP-timecode sync [S150][S151].
- **sACN/E1.31 — stable/entrenched.** ANSI standard, universal receiver support, unmatched multi-source priority/arbitration; but the 512-slot universe model costs ~2.8× packets on pixel loads and slots are 8-bit-only [S157][S150].
- **Art-Net 4 — stable/entrenched.** Actively revised (V1.4 doc rev 2025-10-23), widest install base, ArtSync covers frame coherence; 8-bit slots, no priority field, controller-side unicast-subscription bookkeeping required [S159].
- **OPC — waning.** Flagship implementation archived 2023-05-09; TCP head-of-line blocking is wrong for realtime; do not target [S160][S161].
- **WLED native UDP realtime (WARLS/DRGB/DNRGB) — waning/legacy.** WLED's own ecosystem now points senders at DDP [S152][S165].
- **FPP MultiSync — stable, orthogonal.** Sync-of-stored-content, not pixel transport; not applicable to a live generative engine except as a future pre-rendered mode [S163].

### Cited verdict: what pewpew's Python engine should speak natively

**Primary: DDP over unicast UDP, with per-frame Push, optional broadcast-Push for multi-receiver coherence.** Rationale: (1) it is the only transport whose wire format carries pewpew's quality goals — native 16-bit-per-channel pixel data [S150]; (2) 2.8× fewer packets than sACN/Art-Net per frame directly relieves the actual bottleneck, per-packet processing on ESP32-class receivers — WLED's docs recommend DDP for exactly this reason [S165][S150]; (3) offset semantics make a 10k-pixel frame a trivial scatter of buffer writes with a Push, and delta-frames are free [S150]; (4) every receiver tier pewpew targets already accepts it (WLED/WLED-MM for DIY, Falcon/Kulp/Genius for big rigs) [S164][S152]; (5) a full sender is ~100 lines of Python, proven by LedFx [S156]; (6) the protocol is open and royalty-free with no trademark strings attached [S150], unlike Art-Net [S159].

**Secondary (compatibility output, lower priority): sACN E1.31 unicast** — for interop with lighting consoles and receivers that predate DDP, and because its priority field lets pewpew coexist with a console on shared rigs [S157]. Art-Net output is a nice-to-have third (media-server interop) [S159]. Do not implement OPC or WLED-native modes [S161][S152].

**Caveat (single-source risk):** DDP's sync-under-load behavior on real WLED receivers (does broadcast-Push actually land within a frame across N devices on WiFi?) is asserted by spec and docs but not measured by any source found; a benchmark is queued below.

## Code-reading queue

1. **LedFx/LedFx `ledfx/devices/ddp.py` (+ `networked.py`)** [S156, pinned 566de0f] — how an existing Python engine packs DDP: packet slicing at 480 px, sequence-number use, push-flag placement, async send strategy. Answers: what a production Python DDP sender must handle beyond the spec.
2. **wled/WLED `usermods`/`src` UDP realtime path (`udp.cpp`, `e131.cpp`)** — how the dominant receiver parses DDP/E1.31/DNRGB, what it does with Push, offsets, out-of-order packets, and the realtime-timeout; whether DDP RGBW/16-bit types are honored or ignored. Answers: what wire features are *actually usable* against WLED today.
3. **FalconChristmas/fpp `src/channeloutput/DDP*.cpp`** — reference DDP sender at 10k+ pixel scale: packet pacing, per-frame push, multi-controller fan-out ordering. Answers: pacing strategy for large frames without receiver overrun.
4. **Hundemeier/sacn (Python)** — sACN sender library API/quality; whether to depend on it vs write one; how sync packets and per-universe pacing are exposed. Answers: cost of the sACN compatibility output.
5. **FPP ControlProtocol / MultiSync implementation (`MultiSync.cpp`)** [S163] — only if pre-rendered-show mode is ever scoped.

## Open questions

- **Broadcast-Push coherence on WiFi:** no source measures skew between N WLED receivers latching a broadcast DDP Push (or sACN sync / ArtSync). Settled by: bench test with 3+ ESP32s and a photodiode/logic-analyzer rig (same method as [S166]).
- **Receivers per AP:** community guidance is qualitative ("WiFi becomes the limiting factor" [S165]); no cited number for how many concurrent 60 fps unicast streams one AP sustains. Settled by: airtime math + empirical test, or a targeted forum ask (xLights/Falcon Discourse).
- **WLED 16-bit DDP handling:** WLED-MM docs list 16-bit as a DDP *format* [S152], but whether stock WLED or WLED-MM applies 16-bit data with temporal dithering (vs truncating to 8) is unverified — code read #2 settles it.
- **DDP timecode (T-flag) support in the wild:** spec-optional; unknown whether WLED/Falcon/FPP implement NTP-timecoded display at all. Code reads #2/#3 settle it.
- **200–388 ms noisy-WiFi delay figure** [S168] is a forum anecdote, kept as worst-case color only [NEEDS-VERIFICATION].
- **10 ms audio-visual sync perceptual budget** — defer to RA-10 for a cited perceptual threshold.
