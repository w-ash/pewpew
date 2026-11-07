<!-- Excerpt from ewowi/projectMM@d5ee07ce3d6c590019cbbde670de8c532b2df511
     docs/architecture.md lines 202, 285-318 and 403-414. GPL-3.0, ewowi (Ewoud Wijma) /
     MoonModules contributors. Source entry [S715]. -->
<!-- line 202 (integer math preferred over float in per-light work) -->
- **Integer math preferred over `float` in per-light work.** ESP32's FPU is single-precision and not as cheap as integer ALU; per-light float compounds fast. Use fixed-point or scaled integer math where the visual difference doesn't justify the cost.
<!-- lines 285-318 (the pipeline: per-Layer effects, modifiers, buffer and LUT, blended and mapped) -->
## The pipeline

Modules in the light pipeline can be added, replaced, or removed dynamically at runtime.

```text
              Layouts (shared by every Layer in Layers)
                ├── GridLayout  ──→ coordinate iterator
                └── WheelLayout ──→ coordinate iterator
                        │
                    Layers
                ┌───────┼───────┐
                ▼       ▼       ▼
            Layer A  Layer B  Layer C
          Effect(s) Effect(s) Effect(s)
        Modifier(s) Modifier(s) Modifier(s)
        Buffer(own) Buffer(own) Buffer(own)
            LUT(own) LUT(own) LUT(own)
                │       │       │
                └── Blend+Map ──┘
                        │
                    Drivers          (owns Correction: brightness + lightPreset)
                ├── WS2812Driver  ─ apply Correction ─→ DMA buffer
                ├── ArtNetDriver  ─ apply Correction ─→ UDP packets
                └── PreviewDriver (raw buffer, no Correction) ─→ WebSocket
```

**Data flow.** The pipeline instantiates both core data-exchange shapes (see [§ Data exchange between modules](#data-exchange-between-modules)):

- *Shared-struct (pull):* `Drivers` hands every child driver a `Buffer*` (source) plus a `Correction*` (shared brightness/reorder/white), and `Layer` exposes its pixel buffer to `Drivers` directly on the identity-mapping fast path: each consumer holds a `const`-pointer and reads it per frame. The pointers are **(re)bound on every rebuild**, not just at boot: `Drivers::onBuildState()` re-resolves the active `Layer` (`Layers::activeLayer()`) and calls `passBufferToDrivers()`, which re-runs `setSourceBuffer()`/`setLayer()` on each child (clearing them to `nullptr` when there is no active Layer). So a held pointer is valid only until the next rebuild — which is exactly why the consumers re-read it each frame and tolerate a null (the [robustness rule](#robustness)): a Layer add/delete/replace re-binds or clears it live, no dangling reference.
- *Push to a core sink:* `PreviewDriver` owns the preview wire format (a one-time coordinate table + per-frame RGB point list) and pushes the bytes to a `BinaryBroadcaster` (the core HTTP server). The server broadcasts them over WebSocket without knowing they're a preview: the format and the light types stay entirely in the driver. See [PreviewDriver](moonmodules/light/drivers/PreviewDriver.md).

**Graceful degradation under transport backpressure.** The preview is the project's worked example of a property worth naming generically, because it is the transport-side sibling of the memory-side [§ Degradation cascade](#degradation-cascade): when a consumer can't keep up, **shed quality first** — degrade the stream rather than reach for a stall. The link to a browser is the slow consumer; a full-resolution frame (128² = 16384 lights = ~49 KB) may not drain in the budget one tick allows. Rather than block the loop until it drains, the producer **degrades**, shedding in the order video streaming does — frame rate first, then resolution: (1) the full-resolution frame streams from the driver buffer with no intermediate copy, drained a memory-adaptive chunk per transport tick (a **resumable** send), and the next frame starts only when the previous one finished — so the **effective frame rate self-limits** to what the link sustains, with no loop stall and no connection drop; (2) only when even one frame can't drain promptly does it shed **resolution** via a spatial-lattice downsample, the same congestion-responsive, adaptive-bitrate idea behind HLS/DASH/WebRTC applied to a binary WebSocket. The point budget is itself memory-derived (per [§ Scaling to available memory](#scaling-to-available-memory)), so a tighter board downsamples sooner. The render loop is charged only a bounded slice per tick; each delivered frame is a faithful **complete** frame at a lower rate or coarser sample — a WebSocket message is atomic to the browser, so a frame is whole or absent, never partial/torn. The coordinate table and the downsampled frames take a bounded synchronous send (begin/push/end): a client whose socket stays blocked past the spin budget is closed and reconnects (the browser re-handshakes and the next coordinate table re-primes it) — the bound caps tick occupancy, and a reconnect is a brief blip rather than a frozen preview. This is *graceful degradation*: a fast link sees every light at full rate, a slow link sees a faithful coarser sample at a few fps, and a wedged client is dropped and recovers rather than stalling the device. The mechanism (resumable cross-tick send + drop-new backpressure — a frame offered while one is in flight is dropped, the in-flight one is kept — plus adaptive frame rate + adaptive lattice) lives in `PreviewDriver` + `HttpServerModule`; it is payload-agnostic, so other bulky streams can ride the same transport.

**Naming convention.** Capital `Layouts`, `Layers`, `Drivers` are class names (always capitalised when referring to the class). Lowercase "layouts", "layers", "drivers" is the English plural, used freely when context makes it clear. Singular "layout", "layer", "driver" is an individual instance.
<!-- lines 403-414 (robustness rules: every grid size; phase kept in an accumulator) -->
### Robustness rules

**Effects must run at every grid size.** Modifiers can shrink the logical grid to any size including 0×0×0 (e.g. every layout child is disabled). An effect's `loop()` must produce a correct result for any `(width, height, depth)`: no crashes, no divide-by-zero, no out-of-bounds writes. On a zero grid the loop is a clean no-op. Effects either gate at the top (`if (w <= 0 || h <= 0) return;`) or write their loops so an empty range is naturally a no-op (`for (y = 0; y < h; ...)`).

**Effects must animate at every tick rate.** Per-tick phase math computed as `dt * bpm * K / 60000` truncates to 0 on devices where `dt < 234/bpm` ms: desktop ticks every 0–1 ms, so even bpm=60 freezes. The fix is to keep the raw `dt * bpm` numerator in the phase accumulator and divide only at the read site:

```cpp
phase_num_ += static_cast<uint64_t>(dt) * bpm;
uint8_t t = static_cast<uint8_t>((phase_num_ * 256) / 60000);
```

See NoiseEffect / MetaballsEffect for the canonical pattern. Animation speed must depend only on `bpm` and wallclock, not on tick rate or grid size.
