# ADR-019: Resilience & degradation policy — resilient over perfect

Status: Proposed (2026-07-10)

## Context

The mesh tier is 25–150 battery-powered fixtures outdoors. Hardware WILL
break: connectors corrode, batteries sag, radios wedge, firmware crashes.
ADR-015/016 already make the *fleet* resilient (leaderless convergence,
partition-as-non-event, dual-slot OTA rollback, fungible nodes). This ADR
decides the *node-level* survival policy, the failure-forensics minimum,
the rollout discipline, and the practice regime (chaos drills, burn-in,
spares) — the difference between a fleet that degrades and a fleet that
fails. Evidence base: RA-21.

## Decision

1. **Degradation ladder — four rungs, every transition decided by local
   timers/watchdogs, never consensus** (the show-control convention):
   - **L0 coordinated**: normal gossip + beat participation.
   - **L1 autonomous**: on ~2.5 s beacon silence (the sACN data-loss
     timeout convention), keep rendering locally with last-known
     parameters. Gossip liveness moves nodes L0↔L1 only.
   - **L2 neutral default**: after any reset, boot into a designed default
     scene — never replay stale looks across a power cycle (the DMX
     power-up rule).
   - **L3 safe mode**: after ~10 failed boots, a minimal firmware that
     joins WiFi for OTA and blinks a distress pattern; boot counter
     increments *first thing* in app_main (the documented ESPHome gap:
     crashes before the counter update defeat safe mode).
2. **Watchdog stance — reboot-don't-wedge**: IWDT on; TWDT with
   `CONFIG_ESP_TASK_WDT_PANIC=y` (default only prints a warning) and
   render/RX/telemetry tasks subscribed, fed from task context never timer
   ISRs; bootloader RTC WDT on; plus an **application-level RX-silence
   supervisor** (radio re-init → `esp_restart()` escalation) because the
   WiFi stack can wedge past every default watchdog. Self-reboot on anomaly
   is policy (crash-only software), record-reason-first, loop-guarded by L3.
3. **Forensics minimum — every corpse carries its black box**: 64 KB
   coredump-to-flash partition; two-source reset-reason recording
   (software-marked intent beats hardware register; cleared-on-read so each
   boot attributes one cause); boot/crash counters in RTC-noinit (loop
   detection) + NVS one-write-per-boot (lifetime odometry); the ADR-016
   status beacon carries firmware version, last reset reason,
   unexpected-reset count, min-ever-free-heap, battery state; core-dump
   summaries retrievable over the wire in maintenance windows.
4. **Rollout rings — pinned, not percentaged**: R0 bench (2–5 nodes, tests
   + fault-drill soak) → R1 canary (~5 pinned fixtures, ≥1 of each hardware
   variant; promotion gate: one full duty cycle with **zero** unexpected
   resets) → R2 fleet in the next maintenance window. Per-node rollback is
   automatic (dual-slot, ADR-016); fleet-level halt is human-on-telemetry —
   percentage abort thresholds are meaningless at N≈5. **Corollary: the
   ADR-014 frame carries a schema version and evolves additively** — rings
   guarantee mixed-version operation during every rollout.
5. **Chaos drills, ADR-015's claims as steady-state hypotheses**: packet
   loss in the twin (convergence stays 2–3 intervals at 20 % loss);
   node-kill/partition drills (survivors hold L0/L1, rejoin converges
   unaided); brownout via programmable supply (clean reset reason, no NVS
   corruption); co-channel WiFi traffic as the *legal* interference proxy;
   deliberate boot-loop on a canary (≤10 boots to safe mode). Drills run in
   pre-show soak — the pre-event window *is* the careful-production
   experiment — never mid-show.
6. **Burn-in + spares**: every new/repaired fixture runs a 24–48 h dynamic
   soak (real firmware, radio on) before show-eligibility, doubling as its
   R0/R1 window; spares by Poisson at 95 % fill on an assumed-and-flagged
   2–5 %/season failure rate → **4–6 complete spare fixtures per 50**,
   re-derived annually from the fleet's own telemetry (no published
   ESP32-class field failure priors exist — the fleet is its own actuary).
   Field policy: **swap-don't-debug**; bag the corpse with its black box,
   read it on the bench. IP67 screw-lock connectors, strain relief at
   glands, conformal-coat controllers, reserve potting for connector
   backshells (coat-don't-pot: serviceability is a resilience feature).

## Consequences

- A dead node is a 2-minute swap and a later bench read, not a mid-show
  debugging session; a bad release reverts per-node automatically and
  fleet-wide by not being promoted.
- The neutral-default rule (L2) means a mid-show reboot is a visible-but-
  graceful blip (node rejoins gossip and converges in ~2–3 beacons,
  ADR-015) rather than a stale-look zombie.
- Costs accepted: ~10 % fleet cost in spares; 1–2 days of soak per fixture
  batch; the L3 safe-mode firmware is a small standing maintenance burden;
  schema-versioned frames spend ~1 byte of the payload budget.
- Unexpected-reset count becomes THE fleet health metric (the Memfault
  pattern) — it gates ring promotion and headlines telemetry.
- Bench items feed this policy: brownout threshold vs cold-battery TX sag
  and coredump-summary-over-mesh size are open bench questions (RA-21).

## Evidence

- [S1224] sACN E1.31 2.5 s data-loss timeout; [S1223] DMX hold-last-look
  with all-levels-zero at power-up — the show-control precedents for L1/L2
  and for local-timer decisions.
- [S1200] TWDT default merely warns; panic config required.
  [S1215] Feed from task context, not timer ISRs. [S1201] Bootloader RTC
  WDT. [S1206] Brownout detector defaults (S3 ≈2.44 V, Espressif's own
  estimate caveat).
- [S1209] esp-idf #9400-class WiFi-stack wedge past default watchdogs —
  why the app-level RX-silence supervisor exists.
- [S1222] Crash-only software (Candea & Fox) — the reboot-don't-wedge
  stance.
- [S1210][S1211] ESPHome safe-mode + boot-counter-first discipline (its
  documented gap is the lesson).
- [S1202][S1203] ESP-IDF coredump-to-flash + runtime retrieval API;
  [S1204] `esp_reset_reason()` taxonomy + min-free-heap; [S1213][S1212]
  Memfault two-source reset reasons, graceful forensics degradation —
  design reference; [S1208] RTC-noinit persistence classes; [S1205] NVS
  endurance (one write per boot is a non-issue).
- [S1216] Google canary sizing: small populations catch gross failures,
  small fleets substitute time for population; few stack-ranked metrics.
- [S1218] balena per-device release pinning — the small-fleet canary
  mechanism; [S1217] AWS IoT Jobs exponential rollout + abort thresholds
  (the machinery that does NOT transfer at N=50); [S1214] Memfault
  cohorts/staged rollout + fleet-health-by-version charts.
- [S1220] Chaos-engineering principles (steady-state hypothesis, blast
  radius); [S1221] µChaos survey: embedded chaos tooling is thin and
  Zephyr-only — mechanics are ours to build on the ADR-017/018 loops.
- [S1227] Burn-in practice (8–48 h dynamic, infant mortality);
  [S1228] Poisson spares provisioning method; [S1229] outdoor-pixel field
  failure modes (waterproofing/connectors dominate) + IP67 practice;
  [S1226] conformal coating vs potting tradeoffs; [S1225] battery capacity
  vs temperature (≈50 % at –18 °C; cycle-life loss when hot).

## Rejected alternatives

- **Consensus- or operator-decided degradation** — adds a coordination
  dependency to the failure path itself; show-control precedent is local
  timers [S1224][S1223].
- **Default watchdog config** — TWDT-warns-only ships nodes that wedge
  politely [S1200]; observed WiFi-stack wedges escape it anyway [S1209].
- **Hold-last-look across resets** — replaying stale state after power
  loss is the DMX-documented wrong answer [S1223].
- **Percentage-based rollout automation** (AWS-style) — degenerate at
  N≈50 where one canary is already 20 % [S1217][S1216].
- **Potting everything** — kills swap-don't-debug serviceability and adds
  thermal-cycling solder stress [S1226].
- **Field debugging** — second faults under show pressure; crash-only
  operations instead [S1222].
- **Waiting for published failure-rate priors** — none exist for this
  hardware class [S1228][RA-21]; assume, flag, and measure our own.
