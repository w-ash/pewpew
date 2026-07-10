# ADR-015: Mesh group tier — leaderless coordination: epoch gossip + optional firefly beat phase

Status: Proposed (2026-07-09)

## Context

The mesh group tier (ADR-014) coordinates over lossy fire-and-forget
broadcast: ~11-byte frames at ~10 Hz, no ACKs, no membership, no central
clock, nodes joining/failing/partitioning at will. The tier needs: (a) shared
scene/palette/parameter state that a host can edit live and see converge
fleet-wide fast (the "live playground" requirement); (b) optional shared
musical tempo *and* downbeat phase; (c) spatial waves of activity propagating
between neighboring groups; (d) graceful partition/rejoin. RA-15 surveys the
coordination literature; the two clock-mirroring protocols already documented
in RA-04 (FPP MultiSync, WLED UDP sync) both presuppose a master.

## Decision

A layered stack, all layers riding the same ~11-byte fixed-layout 10 Hz
broadcast (ADR-014); no layer uses ACKs, membership, routing, or a global
clock:

- **Layer 0 — membership-free broadcast.** Every node beacons its whole
  coordination state at ~10 Hz and listens promiscuously. There is no join
  and no neighbor list; partition tolerance falls out.
- **Layer 1 — parameter state as an epoch'd LWW register (gossip).** The
  frame carries `(session_id, epoch, param bytes)`; merge = lexical max on
  `(session_id, epoch)` with RFC 1982 wrap-safe serial compare. This is a
  state-based CRDT: every beacon is an anti-entropy exchange, every node an
  unwitting relay. Event-triggered rebroadcast on hearing a newer epoch uses
  Trickle semantics — suppression (stay silent after k consistent copies) and
  reset-on-inconsistency — never naive flood-on-change. **Single-writer
  discipline**: the host/gateway is the sole parameter author; epochs only
  increase within a session; the random per-boot `session_id` guards against
  stale-epoch zombies.
- **Layer 2 (optional) — beat as a pulse-coupled oscillator.** BPM is just a
  Layer-1 parameter; downbeat *phase* runs as a Mirollo–Strogatz oscillator
  nudged by heard pulses, with the Reachback Firefly Algorithm discipline:
  random stagger of the pulse within the period (sender announces its offset
  in-frame), reachback (apply summed corrections at the next period
  boundary), refractory window, conservative coupling. Timestamp-free, so
  phase accuracy is bounded by channel jitter (few ms) — well inside a
  tens-of-ms beat budget.
- **Layer 2b — waves as gradient/activation fields, not literal CA.**
  Neighbor-propagated effects are monotone activation/gradient relays
  (amorphous-computing style) that self-heal under loss; synchronous-tuned
  Life-class rules are explicitly rejected. One inter-group step per 10 Hz
  beacon (~100 ms) sits inside the apparent-motion window.
- **Layer 3 (optional, off by default) — absolute clock.** Gateway reference
  ticks for convenience; GPS/PPS per node/cluster for installs that truly
  need wall-clock action. Never required for coordinated autonomy.

## Consequences

- A host parameter edit converges fleet-wide in **~2–3 beacon intervals
  (~200–400 ms) at 50 nodes even at ~20 % loss** — the live-playground
  budget (M-4) is met with no central engine and no extra traffic; each
  radio hop beyond gateway range adds ~1 interval.
- Partition/rejoin is a non-event: partitions stay internally coordinated;
  on merge, max-epoch wins deterministically and PCO subgroups re-lock (a
  tempo snap on rejoin is the accepted cost of leaderless operation).
- Multiple concurrent writers are out of scope; if on-node UIs ever write
  during partition, upgrade the epoch to a Lamport pair (+1 ID byte).
- Event rebroadcasts must stay suppression-gated or the fixed-rate design
  degenerates into broadcast storms.
- The PCO phase floor and convergence time at exactly ESP-NOW parameters are
  reasoned from theory + RA-13 latency, not measured — bench item (§12).

## Evidence

- [S900] Mirollo–Strogatz: pulse-coupled oscillators provably synchronize
  exchanging events, not clock values — the timestamp-free foundation.
- [S901] Reachback Firefly Algorithm (SenSys 2005): PCO on real lossy
  multi-hop radios; the three fixes (stagger, reachback, MAC timestamps)
  and ~100–150 µs spread at 24 nodes; time-to-sync ∝ 1/ε.
- [S903] Klinglmayr/Bettstetter: convergence proven on arbitrary connected
  topologies with delays where *stochastic pulse delivery is part of the
  proof* — packet loss stretches convergence, never breaks it.
- [S905][S906] Demers anti-entropy/rumor-mongering + Karp push-pull bounds:
  O(log N) epidemic convergence; over physical broadcast with an 11-byte
  state, anti-entropy is free (every beacon carries full state).
- [S907] State-based CRDTs: monotone-semilattice merge ⇒ Strong Eventual
  Consistency under loss/reorder/duplication — the LWW max-epoch register
  in ~2 bytes.
- [S912] RFC 1982 serial-number arithmetic: wrap-safe epoch compare; the
  session-ID guard against zombies.
- [S910][S911] Trickle (RFC 6206): suppression + reset-on-inconsistency,
  production-proven in RPL; density-logarithmic transmission scaling.
- [S913][S914] Asynchronous-CA literature: synchronous-tuned rules cross a
  phase transition and dissolve under α-asynchrony — why literal CA is
  rejected.
- [S915] Amorphous computing: gradient/diffusion fields on unreliable,
  unsynchronized local broadcast — monotone relay self-heals like the epoch
  merge.
- [S916] Apparent-motion window (~30–400 ms ISI, optimum near ~60 ms):
  10 Hz inter-group stepping reads as coherent motion
  [NEEDS-VERIFICATION — encyclopedic summaries; confirm against primary
  perception sources before treating as a hard bound].
- [S918] GPS/PPS timing modules: ~15–30 ns 1PPS — the absolute-clock escape
  hatch with zero radio coordination.

## Rejected alternatives

- **FPP MultiSync as tempo mechanism** — master playback pointer over stored
  sequences; reintroduces the designated master and pre-rendered content
  [S163].
- **WLED UDP sync as coordination** — state mirroring with no continuous
  phase; it validates state-mirroring-without-central-engine but cannot hold
  a beat [S158].
- **Literal synchronous CA rules (Life-class)** — dissolve under the
  asynchrony/loss the medium imposes [S913][S914].
- **Version vectors** — O(writers) bytes blows the 11-byte budget; pointless
  at one writer [S909].
- **FTSP-style flooding time-sync** — µs-class but needs MAC-layer TX
  timestamps ESP-NOW does not expose to application code; revisit only with
  firmware-level access [S917].
- **Always-on absolute clock (GPS on every node)** — per-node BOM + sky-view
  requirement for a guarantee the PCO layer already meets perceptually
  [S918][S900].
