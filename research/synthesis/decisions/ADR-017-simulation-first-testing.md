# ADR-017: Simulation-first testing & the fleet digital twin

Status: Proposed (2026-07-10)

## Context

pewpew's development — much of it by coding agents — needs feedback loops
whose speed matches where the risk lives. The render core is already pure
and golden-testable (§8, RA-11). The mesh tier's coordination logic
(ADR-015: epoch gossip, PCO beat, gradient fields) is the next-largest risk
mass, and the radio boundary is absolute: no emulator in 2026 exercises
ESP-NOW — Wokwi's request has been open since 2022, Espressif's QEMU
explicitly does not emulate WiFi/BLE/RMT, and Renode has no ESP32 platform.
Everything above the radio can and must run deterministically on the host;
everything below it needs the bench (ADR-018).

## Decision

- **Feedback pyramid** (test-and-feedback.md §1): L1 pure-Python host tests
  → L2 deterministic fleet sim → L3 emulation (thin, bounded roles) → L4
  bench → L5 fleet telemetry. Work runs at the lowest level that can
  falsify it; hardware confirms, never iterates.
- **L2 is a first-class deliverable: the fleet digital twin** — a
  deterministic simulation of 25–150 nodes running the real coordination
  code (gossip merge, PCO, gradient fields) over a modeled lossy broadcast
  medium, with injectable faults (per-link loss, partitions, node churn,
  clock drift). Contract: **same (nodes, schedule, seed) → byte-identical
  trace**, so fleet behavior is golden-testable exactly like render frames.
  Interfaces already scaffolded in `src/harness/fleetsim.py`.
- **Property-based testing is the default above the radio line**:
  Hypothesis round-trip properties for the 11-byte codec; the CRDT merge
  laws (associativity/commutativity/idempotence) as one-line properties;
  `RuleBasedStateMachine` for protocol interaction sequences
  (deliver/drop/duplicate/reorder, join/leave) with epoch-monotonicity
  invariants; PCO convergence as a statistical property over seeded
  topologies.
- **The C frame parser is host-compiled and fuzzed** (AFL++ on the
  stub-the-IDF pattern Espressif itself uses for mDNS), and
  **differentially tested** against the Python codec — any divergence is a
  bug in one of them.
- **Emulation roles, bounded**: QEMU-S3 (`idf.py qemu`) for boot/NVS/OTA
  state machines and task-structure tests; Wokwi for WiFi-STA/DDP receiver
  logic and RMT-TX smoke tests. Neither touches mesh-radio or timing
  claims; timing measured in emulators is explicitly untrusted.
- **Golden artifacts across levels**: golden frames (L1, shipped in
  `src/harness/`), golden fleet traces (L2), decoded-waveform goldens from the
  bench (L4) — all compared with tolerance appropriate to the level.

## Consequences

- Agents iterate at ms latency on the logic that matters most; a mesh
  coordination bug is reproducible from a seed instead of a desk of
  hardware. The twin also powers the §8 preview (watch the simulated fleet
  render) and the chaos drills of ADR-019.
- The twin's radio model is a model: airtime/PDR constants come from RA-13
  and are calibrated against bench item 15 — the twin must never be the
  *source* of RF truth, only the consumer.
- Two sim/real divergence risks are accepted and bench-checked: PCO phase
  floor (item 16) and hidden-node loss patterns (item 15).
- No published precedent exists for sim-first embedded agent iteration
  (Espressif's own agent workflow is hardware-only) — pewpew is leading
  here; expect to write up findings rather than look them up.
- Determinism constraints bind the implementation: no wall-clock, no
  unseeded RNG anywhere in coordination code (the same discipline the
  render core already has, req Q-5 / golden frames).

## Evidence

- [S1113] Wokwi: ESP-NOW unsupported, feature request open since 2022-11 —
  with [S1100][S1101]: what Wokwi *does* cover (S3 GPIO/SPI/RMT-TX partial;
  MAC-level WiFi-STA + UDP), defining its bounded role.
- [S1106][S1105] Espressif QEMU: first-class `idf.py qemu`, S3 supported;
  WiFi/BLE/RMT/I2S explicitly not emulated; Ethernet as network substitute.
- [S1110][S1109] Renode: real multi-node BLE/802.15.4 media, no ESP32
  platform — months of platform work, not configuration.
- [S1138][S1139] Hypothesis (MPL-2.0, active 2026): `@given` round-trips,
  stateful RuleBasedStateMachine with invariants and shrinking — the
  protocol-model test method.
- [S1142] Espressif esp-protocols mDNS host harness: IDF-stubbed Linux
  build + AFL++ on the receive path — the fuzzing template.
- [S1141][S1140] AFL++ active (AGPL-3.0 since v5.00c, tool-use unaffected);
  libFuzzer maintenance-only — pick AFL++.
- [S1169] Espressif's 2026 agent workflow uses real hardware as ground
  truth — the absence of sim-first embedded practice in the literature.
- [S1150] 2026 agent doctrine: give the agent the cheapest verifiable
  check; verify before hardware.
- [S516][S517][S518] Golden-frame gap and the pytest-mpl tolerance model
  (RA-11) — the L1 foundation this ADR extends upward.

## Rejected alternatives

- **Hardware-first iteration** (the documented embedded norm [S1169]) —
  minutes-per-cycle feedback for logic that runs in ms on host; wrong side
  of the pyramid for a mostly-agent-built system [S1150].
- **Full-fidelity chip emulation as the twin** — no ESP-NOW-capable
  emulator exists to build on [S1113][S1106][S1110]; writing a Renode S3 +
  radio model is months of work serving a protocol question the Python twin
  answers directly.
- **Example-based tests for the protocol layer** — the CRDT/codec
  properties are algebraic laws; property testing covers the input space
  example tests cannot [S1138].
- **Trusting emulator timing** — Wokwi caps simulated CPU clock for speed
  [S1100]; QEMU is not cycle-accurate for these peripherals [S1106]; all
  timing claims route to the bench.
