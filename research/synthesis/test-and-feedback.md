# pewpew — test, feedback & resilience architecture

Date: 2026-07-10
Status: Proposed (Phase 5 synthesis). Decisions link to
[ADR-017](decisions/ADR-017-simulation-first-testing.md),
[ADR-018](decisions/ADR-018-agent-driveable-bench.md),
[ADR-019](decisions/ADR-019-resilience-policy.md); requirements referenced as
`T-*` live in [requirements.md](requirements.md). Evidence: RA-19 (embedded
test loops), RA-20 (agentic feedback loops, 2026 practice), RA-21 (fleet
resilience).

Design stance, stated once: **the most resilient system, not the most
perfect one.** Hardware breaks; the loops below exist so that when it breaks,
a human or an agent finds out in seconds-to-minutes with a machine-readable
artifact in hand — and so the fleet itself degrades instead of failing.

## 1. The feedback pyramid

Five levels, cheapest and fastest at the bottom. Work runs at the lowest
level that can falsify it; hardware exists to *confirm*, not to *iterate*
([ADR-017]). The 2026 agent-practice doctrine says the same thing from the
other side: give the agent the cheapest verifiable check first [S1150].

| Level | Environment | Latency | What runs here | Feeds |
|---|---|---|---|---|
| L1 | Pure Python on host (`src/harness/`) | ms | render core golden frames [S518][S516]; codec round-trip, CRDT merge laws, protocol state machines via Hypothesis [S1138][S1139]; PCO convergence statistics over seeded topologies | every commit; agents live here |
| L2 | Deterministic fleet sim (the mesh digital twin, [ADR-017]) | ms–s | gossip/PCO/gradient-field behavior at 25–150 simulated nodes; fault injection: loss %, partition, churn — same seed → byte-identical trace | golden fleet-traces; chaos drills in sim [S1220] |
| L3 | Emulation — honestly thin | s–min | QEMU-S3 (`idf.py qemu`): boot, NVS, OTA state machines, task structure — no radio, no RMT [S1105][S1106]; Wokwi: WiFi-STA/DDP receiver logic + RMT-TX smoke, **no ESP-NOW** [S1100][S1101][S1113] | firmware logic tests without a desk |
| L4 | The bench ([ADR-018]) | min–days | everything the radio boundary forces to hardware: ESP-NOW PDR, PCO spread, dither photometry, coexistence soaks, power profiling | pass^k-gated results [S1154]; soak daemons [S1123] |
| L5 | Deployed fleet | continuous | status-beacon telemetry, reset-reason/crash counters, version skew ([ADR-016], [ADR-019]) | read-only to agents [S1171]; the fleet is its own actuary [S1228] |

**The radio is the hard boundary** — confirmed three independent ways: no
emulator anywhere exercises ESP-NOW (Wokwi: open request since 2022
[S1113]; QEMU: WiFi explicitly not emulated [S1106]; Renode: no ESP32
platform [S1110]). So the pyramid is *sim-above / HIL-below*, and the L2
twin carries the coordination logic that would otherwise need a fleet on a
desk. Layer→environment routing table lives in RA-19 (Findings,
"Conclusion").

Two places pewpew leads rather than follows, per the research: nobody
golden-frame-tests LED effects [S516][S517], and **no published practice
exists for sim-first agent iteration on embedded** — Espressif's own agent
workflow is hardware-only [S1169]. L1+L2 are the novelty; L3–L5 are
assembled from established parts.

## 2. The agent feedback-loop contract

From RA-20's findings; every element is CURRENT (2026) practice unless
noted. Full staleness audit in RA-20 §"What changed since 2025".

1. **Verification-first, with the escalation ladder.** Every change gets a
   way to verify itself: inline check → goal condition → blocking hook →
   fresh-context adversarial reviewer [S1150]. Humans review *evidence
   artifacts* (test output, traces, captures), not keystrokes [S1150].
2. **Everything-as-CLI, `--json`, meaningful exit codes.** One verify verb
   per pyramid level (`verify sim`, `verify twin`, `verify qemu`,
   `verify bench <item>`), structured output, failure artifacts readable
   in-context [S1150][S1168]. Interactive-only or screenshot-only feedback
   surfaces are the named anti-pattern [S1150][S1168].
3. **Deterministic gates only where determinism exists.** Hard gates
   (hooks) on L1/L2 — they are seeded and reproducible. **Never hard-gate a
   session on L4**: open-air 2.4 GHz results are distributions, not point
   values [RA-19]; bench results feed a pass^k statistical harness instead
   (k isolated trials, scored, transcripts kept) [S1154][S1170].
4. **The bench is a tool server we write** ([ADR-018]): read-only verbs
   (serial tail, capture read, telemetry query) and actuating verbs (flash,
   power-cycle, pattern-push) in separate namespaces; `--dry-run` on every
   actuating verb [S1168]; audit-logged; permission system as the hard
   layer, not hook string-matching [S1151][S1155]. Existing hardware MCP
   servers are read-for-shape, not dependencies [S1162][S1163].
5. **Soaks are detached jobs, not long sessions.** A bench-host daemon owns
   the soak and appends newline-JSON health records; CI (scheduled
   workflows) and agents poll the artifact — start/poll/cancel semantics,
   MCP-Tasks-shaped [S1159][S1143][S1123].
6. **Fleet tier is read-only to agents, period.** Watch telemetry, file
   findings, propose fixes (the Seer model [S1171][S1172]); actuating the
   deployed fleet never happens from an unattended agent. The literature
   has no worked bench-safety framework [RA-20 §7] — this boundary is ours,
   stated here and enforced in [ADR-018]'s tiers.
7. **Conventions live in the repo file** (AGENTS.md/CLAUDE.md — the 2026
   standard [S1158]), lean, with must-always-hold rules as hooks and
   situational knowledge as skills — instruction-file maximalism is a named
   2025 failure mode [S1150][S1151].

## 3. Resilience principles

Decided in [ADR-019]; the fleet-level primitives (leaderless CRDT gossip,
partition-as-non-event, dual-slot OTA rollback, fungible nodes) are already
ADR-015/016. What this layer adds:

- **Degradation ladder, local decisions only**: L0 coordinated → L1
  autonomous (2.5 s beacon silence, the sACN timeout convention [S1224]) →
  L2 neutral-default-after-reset (DMX power-up rule: never replay stale
  looks [S1223]) → L3 safe-mode firmware (~10 failed boots [S1210]). No
  consensus, no operator in the loop.
- **Reboot-don't-wedge**: TWDT set to panic (the default only *warns*
  [S1200]), app-level RX-silence supervisor because the WiFi stack can
  wedge past every default watchdog [S1209], crash-only stance [S1222].
- **Every corpse carries its black box**: coredump-to-flash, two-source
  reset reasons, RTC-noinit loop counters, NVS lifetime counters; the
  status beacon carries version + last reset reason + unexpected-reset
  count + min-free-heap [S1202][S1204][S1213][S1208].
- **Rings, pinned not percentaged**: R0 bench → R1 ~5 pinned canaries (one
  full duty cycle, zero unexpected resets) → R2 fleet; per-node rollback is
  automatic (dual-slot), fleet halt is human-on-telemetry [S1218][S1216]
  [S1217]. Corollary requirement: **the mesh frame carries a schema
  version** — rings guarantee mixed-version operation ([ADR-014] frame).
- **Chaos drills with ADR-015's claims as the hypotheses** (they are
  falsifiable predictions): loss in sim, node-kill/partition/boot-loop on
  the bench, brownout via programmable supply, co-channel traffic as the
  legal interference proxy; drills run in pre-show soak, never mid-show
  [S1220][S1221].
- **Burn-in + spares**: 24–48 h dynamic soak before show-eligibility
  [S1227]; Poisson at 95 % on an assumed (flagged) 2–5 %/season rate → 4–6
  complete spares per 50 fixtures, revised from own telemetry — no
  published ESP32-class field failure priors exist [S1228][RA-21];
  swap-don't-debug [S1222].

## 4. §12 prototype items, mapped to the pyramid

One-off = run once, record, done. Rig = becomes a permanent scripted bench
capability (pytest-embedded test + instruments per [ADR-018]).

| §12 item | Level | One-off / rig | Instrument path |
|---|---|---|---|
| 1 NumPy throughput | L1 | one-off | host microbenchmark |
| 2 authoring surface | L1 | one-off | pattern-writing study |
| 3 DDP Push skew | L4 | rig | logic analyzer on N data lines [S1126][S1127] |
| 4 WLED 16-bit DDP | L3/L4 | one-off | code read + device check |
| 5 dither bits vs Hz | L4 | rig | TSL257 photometry, IEEE 1789 metrics [S1137] |
| 6 audio-to-photon | L4 | rig | click-to-photodiode timing [S1137] |
| 7 marimapper accuracy | L4 | one-off | known-geometry grid |
| 8 RP2350 ulab 2× | L4 | one-off | fire benchmark on device |
| 9 BLE push speed | L4 | one-off | timed FileTransferService push |
| 10 AP unicast capacity | L4 | one-off | incremental-receiver soak |
| 11 keyframe interp threshold | L4 | rig | photometry rig, vary keyframe rate |
| 12 OKLab on wearable | L1+L4 | one-off | ulab µbench |
| 13 CPython pacing jitter | L1 | rig | 10-min paced-loop soak, tick histogram |
| 14 WLED DDP ingest | L4 | one-off | delivered-fps counter |
| 15 ESP-NOW PDR vs load | L4 | rig | multi-DUT senders + monitor-mode sniffer, scapy PDR, pass^k [S1117][S1136][S1154] |
| 16 PCO phase floor | L4 | rig | GPIO-per-downbeat + logic analyzer spread [S1118][S1127] |
| 17 RMT-DMA / LCD soak | L4 | rig (soak daemon) | 2-week soak, capture-on-trip [S1123][S1125] |
| 18 dither CPU cost | L4 | one-off | cycle counts, radio active |
| 19 gateway latency + BSSID filter | L4 | one-off | Unity TEST_CASE_MULTIPLE_DEVICES two-board [S1118] |
| 20 bridge loss + scan-while-render | L4 | rig | counters both sides + PPK2 rail [S1131][S1132] |

## 5. What is deliberately NOT built

- No device emulator beyond what QEMU/Wokwi give for free (RA-11's
  anti-goal stands; the twin is a *protocol* sim, not a chip sim).
- No RF-shielded chamber: open-air PDR variance is handled statistically
  (pass^k), not eliminated [RA-19][S1154].
- No percentage-based rollout machinery, no fleet-scale OTA orchestration
  service — pinning + windows + telemetry at N≤150 [S1218][ADR-016].
- No hard gate on any hardware test; no unattended agent actuation of the
  deployed fleet [ADR-018].
