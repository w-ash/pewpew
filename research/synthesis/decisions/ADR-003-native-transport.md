# ADR-003: Native transport — DDP over unicast UDP, plus compatibility outputs

Status: Proposed (2026-07-03)

## Context

The host engine ships frames to network receivers every 16.7 ms (R-2). The
candidate wire protocols are sACN/E1.31, Art-Net, DDP, WLED's own UDP
realtime modes, and OPC. At pixel loads the binding constraint on ESP32
receivers is per-packet processing, not bandwidth; and pewpew's 16-bit
pipeline (ADR-001) needs a transport that can carry it (R-3, R-5, R-6).

## Decision

- **DDP is the native transport**: unicast UDP per receiver, offset-addressed
  multi-packet frames, **Push flag set on the frame's last packet**
  (fill-then-latch — no tearing), sequence numbers for loss detection.
- **16-bit DDP** to receivers that support it; 8-bit DDP (host-dithered per
  ADR-002) to stock WLED.
- **Broadcast DDP Push** as the cross-receiver frame-latch signal at room
  scale (R-10) — real-world skew is prototype item #3.
- **Compatibility outputs, not defaults**: sACN/E1.31 and Art-Net sinks for
  commercial controllers that want them; UPXL serial for Pixelblaze output
  expanders; OPC not implemented.
- Never multicast on WiFi; wired Ethernet receivers for the room backbone
  (R-5).

## Consequences

- Day-one interop with WLED, WLED-MM, Falcon, and FPP — all speak DDP.
- The engine's sink API must expose fill/latch semantics so DDP Push and
  future sinks share one contract.
- WLED ignores the DDP timecode flag, so latch timing rides on Push arrival
  — acceptable on a LAN, revisit if timecode support lands upstream.

## Evidence

- [S150] DDP is 94.9% packet-efficient vs sACN 72.7% / Art-Net 85.9%;
  sACN/Art-Net need ~2.8× the packets; DDP is the only surveyed protocol
  with a native 16-bit wire format; Push decouples buffer-fill from
  display; WiFi multicast loss ≈ raw PER (~5%) vs <0.1% for unicast.
- [S165] WLED's own docs recommend DDP because per-packet processing, not
  bandwidth, saturates ESP32 receivers; realtime streaming is steered to
  Ethernet boards.
- [S152] WLED-MM recommends DDP for WLED-to-WLED streaming — field
  confirmation from the receiver side.
- [S645:wled00/e131.cpp#L20-L93][S162] WLED renders non-Push senders
  per-packet — tearing is structural in its own DNRGB protocol; DDP+Push
  avoids the class of bug.
- [S645:wled00/e131.cpp#L63] WLED ignores the DDP timecode flag — the
  documented caveat above.
- [S359] Falcon F16v5 receives DDP natively — the room-backbone controller
  path is covered.
- [S682:README.md#L13-L78][S365] UPXL expander protocol: open/MIT,
  CRC-framed, DRAW_ALL latch, ~66k px/s per 2 Mbps bus — the serial
  compatibility sink.

## Rejected alternatives

- **sACN/Art-Net as native** — ~2.8× packet count at pixel loads and no
  16-bit format [S150]; kept only as compatibility sinks.
- **WLED-UDP realtime modes (WARLS/DRGB/DNRGB)** — per-packet rendering
  tears multi-packet frames [S645:wled00/e131.cpp#L20-L93][S162].
- **OPC** — TCP, 8-bit, waning with Fadecandy; no receiver ecosystem in
  2026 [S016][S160][S027].
- **A custom pewpew protocol** — forfeits the entire stock-receiver fleet
  that makes ADR-004 work [S165][S150]; nothing DDP lacks justifies it
  today.
- **Multicast distribution** — ~5% loss on WiFi vs <0.1% retried unicast
  [S150].
