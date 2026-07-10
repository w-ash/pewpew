# RA-15: Decentralized coordination & synchronization without a central clock

Last researched: 2026-07-09
Status: draft
S-ID block: S900–S949

## Key questions

- Pulse-coupled oscillator (firefly) synchronization: what do Mirollo–Strogatz and the WSN firefly-sync literature (Werner-Allen et al., Tyrrell/Auer/Bettstetter) establish about convergence time vs node count, behavior under packet loss and partition, and achievable phase accuracy? Is beat-phase sync (~tens of ms) achievable over ESP-NOW-class broadcast with no timestamps?
- Gossip/epidemic state dissemination: anti-entropy vs rumor-mongering, convergence bounds, and what versioning discipline (Lamport clocks / version vectors / last-writer-wins / CRDT-lite) fits an ~11-byte fixed payload. Expected fleet-wide convergence latency for one host-injected parameter change at 50 nodes, 10 Hz broadcast, realistic loss.
- Neighbor-state cellular-automata coordination: does the asynchronous-CA literature support running spatial rules (waves, diffusion, GoL-class) over lossy unordered local broadcast? Is 10 Hz per-node state exchange enough for visually pleasing propagation?
- Tempo/beat distribution without clock sync: beat as a slow oscillator (gossiped BPM + firefly phase-nudging) vs master-pointer sync (FPP MultiSync) vs state mirroring (WLED UDP sync) — see RA-04 for the latter two.
- When is a shared absolute clock actually required, and what are the cheapest ways to get one outdoors (gateway reference ticks, GPS/PPS, FTSP-style flooding sync)? Costs and accuracy.
- Partition/rejoin: what happens when the fleet splits and merges; reconciliation strategies for tiny state.
- Failure modes to design against: broadcast storms, oscillator death spirals, stale-epoch zombies.
- **The verdict question:** a layered coordination stack for pewpew's mesh tier — membership-free broadcast → epoch'd parameter gossip → optional firefly phase layer — that stays inside ~11-byte fixed-layout broadcasts at ~10 Hz.

## Findings

### Pulse-coupled oscillator (firefly) synchronization

**The base model.** Mirollo & Strogatz (1990) analyze a population of identical
integrate-and-fire oscillators with pulsatile coupling: when one oscillator
fires, every other jumps its state up by a fixed amount (or to threshold,
whichever is less). For all-to-all coupling and a concave-down state function,
they prove that from almost all initial conditions the population converges to
synchronous firing [S900]. The model is stateless in the sense pewpew needs:
nodes never exchange clock values, only the *event* of a firing — which maps
directly onto a timestamp-free broadcast beacon [S900].

**Making it survive real radios — Reachback Firefly Algorithm (RFA).**
Werner-Allen, Tewari, Patel, Welsh & Nagpal (SenSys 2005) implemented M&S on
TinyOS/MicaZ motes and found three modifications were required [S901]:
1. *MAC-layer timestamping* of the firing message, so receivers can subtract
   the (CSMA-variable) transmission delay [S901].
2. *Reachback response*: instead of jumping phase instantly on hearing a
   firing (which the delayed, queued messages of a real radio would corrupt),
   a node collects all firings heard during the current period and applies
   the summed adjustment at the start of its *next* period [S901].
3. *Pre-emptive message staggering*: because synchronized firing is the CSMA
   worst case (everyone transmits at once), each firing broadcast is delayed
   by a uniform-random 0–D; they used D = 25 ms with period T = 1 s and report
   this "works well to eliminate packet loss during synchronized firings for
   neighborhoods of upto 20 nodes" [S901].

Results on a 24-node indoor multi-hop testbed with lossy asymmetric links
(some links >20% loss, strongly asymmetric cliques): the fleet synchronized to
a 50th-percentile group spread of ~128–154 µs across all tested coupling
strengths, with an apparent accuracy floor around 100 µs set by clock skew and
the FTSP measurement harness [S901]. Time-to-synchronize is proportional to
1/ε (ε = coupling strength): with T = 1 s, ε = 1/100 converged in ~284 s and
ε = 1/1000 in ~1164 s [S901]. Occasional unexplained "dispersive events"
scattered the group by up to ~0.1 s before re-convergence over a few periods —
the 90th-percentile spread in some runs was 3.6–30 ms because of them [S901].
Choice of T does not affect the *number of periods* to converge, only the
wall-clock time and the radio duty cycle; the constraint is T ≫ D [S901].

**Delay-aware variant.** Tyrrell, Auer & Bettstetter (BIONETICS 2006) rederive
firefly sync for ad hoc radios, adding deliberately delayed pulse emission and
refractory periods so that steady-state accuracy is limited only by
propagation delay; simulations cover a 30-node fully-meshed network across
coupling factors [S902][NEEDS-VERIFICATION — full text paywalled; abstract and
secondary summaries only].

**Convergence guarantees under loss.** Klinglmayr, Kirst, Bettstetter & Timme
prove convergence to network-wide synchrony from arbitrary initial conditions
for a class of pulse-coupling response functions on *arbitrary connected
topologies with variable delays* — and show that *stochastic* pulse emission
(unreliable links, probabilistic transmission) is not merely tolerated but is
an ingredient of the convergence proof [S903]. Follow-on hardware work
(Computer Networks 2016) implemented PCO sync with phase-rate correction on
six programmable radio boards and measured sub-microsecond precision — the
first PCO evaluation on real radio hardware [S904]. The practical reading for
pewpew: packet loss randomizes which couplings occur each period, and the
theory says this does not break convergence; it only stretches it [S903].

**Is beat-phase sync (~tens of ms) achievable over ESP-NOW-class broadcast
without timestamps?** The µs-class results above all rely on MAC-layer
timestamps to cancel media-access delay [S901][S904]. Without any timestamp,
the achievable phase error floor is the *jitter* of the send-to-receive path
(CSMA backoff + queueing), because a receiver treats "packet arrived" as "peer
fired now". On a lightly loaded ESP-NOW channel that path is at worst a few
milliseconds (RA-13's latency findings quantify this) — one to two orders of
magnitude below a tens-of-ms beat-phase budget. Two design consequences carry
over directly from RFA even at relaxed accuracy: (a) synchronized firing is
the CSMA worst case, so pewpew's beat beacons must be randomly staggered
within the period and the *stagger subtracted by the sender before it
transmits* (sender-side compensation needs no receiver timestamp: the sender
simply announces "my phase-zero was X ms ago" — but that is a 1-byte field,
not a clock sync); or fire-and-suppress so only a few nodes beacon per beat
[S901]; (b) reachback (apply corrections at period boundaries) is the right
structure when messages arrive late and out of order [S901]. Verdict-level
answer: yes — tens-of-ms mutual beat phase is comfortably inside what
timestamp-free PCO achieves on lossy broadcast radio, given stagger +
reachback [S901][S903].

**Convergence time at pewpew scale.** RFA's 1/ε scaling with the *number of
periods* roughly independent of T [S901] means a beat-layer oscillator with,
say, a 2 s bar period and aggressive ε (loose accuracy target permits large ε
without visible overshoot) should converge in tens of periods — tens of
seconds — for a 25–50 node single-hop-dominated mesh; the M&S theory says
denser (closer to all-to-all) coupling converges faster than the sparse
multi-hop testbed above [S900][S901]. No published measurement exists at
exactly ESP-NOW's parameters; flagged in Open questions.

### Gossip/epidemic dissemination of parameter state

**The two canonical modes.** Demers et al. (Xerox PARC, PODC 1987) define the
vocabulary still in use: *direct mail* (send update to everyone once —
fast but unreliable), *anti-entropy* (periodically compare full state with a
random peer and reconcile — reliable, converges with probability 1, but
touches whole databases), and *rumor mongering* (spread "hot" updates
probabilistically, retire them once enough peers already know — cheap, but a
rumor can die before reaching everyone, so it is backed by anti-entropy)
[S905]. Epidemic spread is exponential: the infected population roughly
doubles per round until saturation, giving O(log N) rounds to reach all N
nodes [S905][S906]. Karp, Schindelhauer, Shenker & Vöcking (FOCS 2000)
sharpen the bounds for push-pull gossip: any address-oblivious algorithm
needs Ω(n ln ln n) messages, and push-pull completes in O(log N) rounds with
high probability [S906].

**pewpew's regime is easier than the literature's.** The classic results
assume *pairwise unicast* exchanges with randomly chosen partners. pewpew's
mesh tier has physical local *broadcast*: one transmission reaches every
in-range node simultaneously. In a single broadcast domain, "gossip" 
degenerates to: every node's periodic 10 Hz state beacon simply *carries the
newest (epoch, value) it knows*. That is anti-entropy where every beacon is a
full state exchange — possible only because pewpew's whole shared state is
designed to fit in one ~11-byte payload. The classic anti-entropy cost
objection (full-database comparison [S905]) vanishes when the database is 11
bytes.

**Convergence latency at 50 nodes, 10 Hz, realistic loss** (computed from the
stated mesh parameters; per-link loss p treated as independent per broadcast).
Single broadcast domain: the gateway's first beacon carrying a new epoch
reaches each node w.p. (1−p); with p = 0.2, ~40 of 50 nodes hold the new
state within one beacon interval (≤100 ms + the gateway's own phase, ≤100 ms).
In the next interval ~41 nodes all beacon the new epoch, and a straggler
misses *all* of them only w.p. p^41 ≈ 10^-29 — i.e., fleet-wide convergence in
2–3 beacon intervals, **~200–400 ms worst-case end-to-end**, dominated by
beacon phase, not loss. Each radio hop beyond the gateway's range adds ≈1
beacon interval (the epidemic-doubling structure of flooding [S905][S906]).
Even at p = 0.5 the second round succeeds w.p. 1−0.5^25 per straggler; loss
moves the tail, not the shape. This satisfies the "live playground"
requirement (host edit visible fleet-wide well under a second) *without any
ACKs, routing, or membership* — the update rides the beacons that are being
sent anyway.

**Trickle: the standardized version of exactly this.** The Trickle algorithm
(Levis et al., NSDI 2004; standardized as RFC 6206) is IETF's distillation of
"gossip a version number over lossy shared media": each node transmits its
version within a randomized window unless it has already heard k consistent
transmissions (suppression); consistent intervals double from Imin up to
Imax; hearing an *inconsistent* (older/newer) version resets the interval to
Imin [S910][S911]. It propagates new data "on the scale of link-layer
transmission times" while idling at a few transmissions per hour, and its
transmission rate scales logarithmically with node density [S910]. Trickle is
proven in production as the dissemination layer of RPL route updates and
firmware/config distribution in LLNs [S910]. For pewpew, the *suppression*
and *reset-on-inconsistency* ideas apply directly; the exponential idle
back-off does not, because the 10 Hz beacon is also serving neighbor-state
(CA) and liveness roles and should keep its fixed cadence. A hybrid is
natural: fixed-rate beacons carry (epoch, params-digest); a node that hears a
*newer* epoch than its own immediately pulls/rebroadcasts (Trickle reset
semantics) rather than waiting out its beacon phase [S910].

**Versioning discipline for an 11-byte payload.** The options, cheapest
first:
- *Monotonic epoch counter + value (single writer).* The host/gateway is the
  only writer of scene parameters; every parameter set carries an epoch it
  increments. Receivers keep max(epoch) and adopt its value. This is exactly
  a last-writer-wins register, the simplest state-based CRDT: merge =
  take-max-epoch is associative, commutative, and idempotent, so replicas
  converge under arbitrary duplication, reordering, delay, and loss (Strong
  Eventual Consistency) [S907]. A 1–2-byte epoch compared with serial-number
  arithmetic (RFC 1982) survives wraparound: comparisons are defined modulo
  2^bits with a half-range window, the same mechanism DNS serials and TCP
  sequence numbers use [S912]. With a 16-bit epoch and half-range 32767, a
  host would have to issue >32k edits while a node sleeps for confusion —
  acceptable; an 8-bit epoch (window 127) is defensible only with a
  session-ID guard (below).
- *Lamport timestamps* generalize this to multiple writers: each node keeps a
  counter, bumps it past any observed value, and ties are broken by node ID —
  giving a total order consistent with causality at the cost of ~1 extra ID
  byte [S908]. Needed only if two hosts (or on-node UIs) can write
  concurrently.
- *Version vectors* (one counter per writer) detect true concurrency rather
  than arbitrating it [S909], but cost O(writers) bytes and are pointless at
  one writer; not viable in 11 bytes beyond ~2 writers. Not recommended.

**What the tiny payload really buys.** Because the merge function is a max on
a totally ordered epoch, *every node is a relay without knowing it is one* —
there is no distinction between "my state" and "forwarded state". This is the
CRDT convergence condition (monotonic semilattice) applied at 2-byte scale
[S907]; no consensus, leader election, or membership protocol exists anywhere
in the loop, which is what makes partition tolerance and self-healing free
(see Partition/rejoin below).

### Neighbor-state cellular-automata coordination

**Can a CA run over lossy, unordered local broadcast?** The synchronous CA
that generates familiar spatial structure (Game of Life, diffusion waves)
assumes every cell updates on a global tick using the same-generation
neighbor states — precisely what pewpew cannot provide. The relevant body of
theory is *asynchronous* CA. Fatès' survey establishes that dropping global
synchrony is not a small perturbation: update policy is a first-class
parameter that can qualitatively change or destroy a rule's emergent
structures [S913]. Blok & Bergersen (Phys. Rev. E 1999) quantified this for
Life specifically with *α-asynchronism* — each cell updates with probability
α per step — and found a critical phase transition (directed-percolation
universality class) as α drops from 1 (fully synchronous) toward the Poisson
limit; below the transition the characteristic Life structures dissolve
[S914]. Practical reading: rules tuned for synchronous updating are fragile
under the random update order pewpew's mesh imposes, so pewpew must either
(a) choose rules known to be robust to asynchrony, or (b) treat lost/late
neighbor updates as the α-asynchronous regime and design for it, not against
it [S913][S914].

**Robustness to lost updates — reframe the CA as a diffusion/gradient field.**
The amorphous-computing literature (Abelson et al., MIT; Nagpal) targets
exactly pewpew's substrate: "vast numbers of unreliable, locally
communicating simple devices" with no global clock and no reliable delivery
[S915]. Its workhorse primitive is the *gradient/diffusion wave*: a source
emits a value, each device relays the min-hop (or min-distance) it has seen,
and the field self-heals as updates propagate — because the operation is a
monotone min over a semilattice, exactly like the epoch merge above, lost
messages only delay the wave, never corrupt the steady state [S915][S907].
Waves and regions of controlled size fall out of relaying while a hop count
stays under a bound [S915]. For pewpew, "waves of activity propagating
between neighbors" are best implemented as gradient/activation fields (each
node broadcasts an activation level or a phase; neighbors relax toward /
trigger off it) rather than as literal Life-rule state machines — the former
degrade gracefully under loss, the latter can collapse [S914][S915].

**Is 10 Hz enough for visually pleasing propagation?** This is a perceptual,
not a networking, question, and the apparent-motion literature bounds it.
Discrete lights switching in sequence are perceived as smooth *apparent
motion* (beta movement) for stimulus-onset/inter-stimulus intervals roughly
30–400 ms; the "optimal" motion percept sits around 60 ms between elements,
below ~25 ms elements look simultaneous and above ~400 ms they look like
disconnected blinking [S916]. A CA/gradient wave that advances one
group-to-neighbor step per 10 Hz beacon interval moves a "front" every 100 ms
— squarely inside the apparent-motion window, near its comfortable middle. So
a wave crossing a line of groups at one hop per 100 ms reads as coherent
motion, not as a stutter of independent blinks [S916]. Two caveats: (1) the
*within-group* render is local and 60 fps, so only the *inter-group
propagation* is rate-limited to 10 Hz — fine, because inter-group spacing is
large (Korte: larger spacing tolerates/prefers longer intervals [S916]); (2)
beacon jitter and loss make the true step interval 100 ms plus a tail — a
dropped update stalls a front for one interval (~100 ms), which is a brief
hitch, not a break, as long as it stays under the ~400 ms fusion ceiling
[S916]. Verdict-level: 10 Hz is sufficient for inter-group wave propagation;
going much slower (≤2–3 Hz, ≥400 ms/step) would break the motion percept.

**Rate requirement summary.** Inter-group propagation needs a beacon interval
comfortably under the ~400 ms apparent-motion ceiling and ideally near
~60–150 ms for the best motion percept [S916]; pewpew's 10 Hz (100 ms) is
well-placed. This is independent of the render frame rate, which stays at
~60 fps locally.

### Tempo / beat distribution without a shared clock

pewpew patterns are time-parameterized functions of t, so "tempo" means the
fleet must agree on both a *rate* (BPM) and a *phase* (where the downbeat
falls). These two quantities decompose along the lines already established:
- **Rate (BPM)** is a slowly changing scalar value — treat it exactly like any
  other parameter: gossip it under an epoch counter, LWW-merge on max-epoch
  [S907]. It changes rarely (a host tempo edit, or an on-node tap-tempo) and
  tolerates the ~200–400 ms convergence of the gossip layer because a BPM
  change is not perceptually instantaneous anyway.
- **Phase (downbeat)** is a fast, continuously advancing quantity that cannot
  be gossiped as a value (it is stale the instant it is sent). This is
  precisely what pulse-coupled oscillators solve: model the beat as a slow
  firefly oscillator with period = one bar (or one beat), have each node emit
  a tiny "downbeat" pulse, and nudge phase toward heard pulses using the
  reachback/staggered discipline [S900][S901]. Because the accuracy target is
  a musical beat (tens of ms is inaudible relative to a ≥300 ms beat at
  ≤200 BPM), the timestamp-free PCO floor (a few ms of channel jitter) is far
  inside budget [S901][S903].

This is a genuinely different architecture from the two clock-mirroring
approaches pewpew's tree already documents in RA-04, and the contrast is the
justification for choosing PCO here:
- **FPP MultiSync** distributes a *master playback pointer* (frame number +
  seconds-elapsed of a stored .fseq) that remotes slew to — it presupposes a
  designated master and pre-rendered content, and carries an absolute frame
  index, i.e. it *is* a lightweight clock-distribution scheme, not a
  leaderless one [RA-04 §FPP MultiSync, S163]. Adopting it would reintroduce
  the central master and the pre-rendered-content assumption pewpew's mesh
  tier exists to avoid.
- **WLED UDP sync** mirrors *state* (preset/effect/brightness) across devices
  so they change together, with no continuous phase alignment — good for
  "everyone switch to scene 3 now", useless for "keep a shared beat phase"
  [RA-04 §WLED native, S158]. It is a coarser version of pewpew's
  epoch-gossip layer and confirms the pattern (state mirroring without a
  central engine) but does not address tempo phase.

So pewpew's tempo layer = (BPM via epoch-gossip) + (downbeat phase via
firefly PCO); neither borrowed clock-mirroring protocol supplies the
leaderless continuous phase alignment [S900][S901][S163][S158].

### When a shared absolute clock is actually needed, and cheap ways to get one

A true shared *absolute* clock (as opposed to mutual phase agreement) is only
required when nodes must act at an externally specified wall-clock instant or
align to sub-ms tolerance the PCO floor cannot reach — e.g. tightly
choreographed strobe hits referenced to a timecode, or audio-reactive effects
that must align to ~10 ms of a live external audio feed shared out-of-band.
For pewpew's stated goals (shared scene/palette/tempo/phase, propagating
waves), mutual phase agreement via PCO is sufficient and an absolute clock is
*not* needed [S900][S901]. Should one become necessary, cheapest-first:
- **Gateway broadcasting reference ticks.** If a host/gateway is present, it
  can periodically broadcast a timestamped tick; nodes discipline a local
  offset. Accuracy is bounded by broadcast jitter (single-hop ESP-NOW: low
  single-digit ms without MAC timestamping) — adequate for beat/tempo, not
  for µs work. Zero extra hardware; single point of failure by design, so the
  PCO layer must continue to hold phase if the gateway drops.
- **FTSP-style flooding time sync.** Maróti et al. (SenSys 2004) flood a
  root's time with MAC-layer timestamping and per-node skew estimation,
  achieving ~1.48 µs single-hop error and ~1 µs *average per-hop* error,
  robust to node/link failure via periodic re-flooding and implicit topology
  update [S917]. It needs MAC-layer TX timestamping, which ESP-NOW does not
  expose to application code — so FTSP-class µs accuracy is *not* directly
  attainable on ESP-NOW without firmware-level access; this is the same
  limitation that caps timestamp-free PCO at ms-class (Open questions).
- **GPS/PPS discipline.** A timing GPS module emits a 1-pulse-per-second
  signal accurate to tens of nanoseconds (u-blox timing modules quote ~15–30 ns
  RMS 1PPS) [S918]. Every node with a GPS gets an independent, drift-free,
  fleet-wide-consistent absolute second boundary with no radio coordination
  at all — the gold standard for outdoor art at scale, at the cost of a
  ~US$10–20 module and a sky view per node (or per cluster). This is the
  cheapest route to *sub-µs fleet-wide absolute time outdoors* and sidesteps
  every radio-jitter problem, but adds per-node BOM and an antenna [S918].

Recommendation: do not build an absolute-clock layer into the base design;
keep it an optional module (gateway ticks for convenience; GPS/PPS for the
rare install that needs hard absolute time), because the PCO phase layer meets
the perceptual requirement without it [S900][S901][S918].

### Partition / rejoin behavior

The leaderless, membership-free, max-epoch design makes partition tolerance a
non-event rather than a handled case:
- **On split**, each partition keeps gossiping the highest epoch it holds and
  keeps its PCO subgroup phase-locked internally; both partitions continue to
  look coordinated *within themselves*. No quorum is lost because there is no
  quorum [S907].
- **On rejoin**, the two epoch streams meet; the LWW max-epoch merge picks the
  higher epoch deterministically and it floods across the reunited fleet in
  the usual 2–3 beacon intervals [S905][S907]. The two PCO subgroups, once in
  radio range again, pull toward a common phase by the same coupling that
  synchronized them initially — Klinglmayr et al. prove convergence from
  *arbitrary* initial conditions on *arbitrary connected* topologies, which is
  exactly the "two locked clusters merge" scenario [S903].
- **Risk at rejoin**: if the two partitions independently advanced epochs from
  a common ancestor (both had a local writer), max-epoch silently discards one
  partition's edits — acceptable for a single-authority (host) design, but a
  reason to keep writes single-writer or Lamport-ordered if on-node UIs can
  edit during a partition [S908]. A short **session/generation ID** (a random
  value the host picks at boot, carried alongside the epoch) prevents a
  stale-but-numerically-higher epoch from a long-partitioned zombie node from
  overriding a fresh session: compare (session, epoch) lexically, newest
  session wins [S912].

### Failure modes to design against

- **Broadcast storms.** Naive "rebroadcast on every change" flooding
  collapses a shared medium — the classic broadcast-storm problem. Trickle's
  suppression (stay silent if you have already heard k copies of the current
  version this interval) is the standard mitigation and bounds channel use
  regardless of density [S910]. RFA's pre-emptive random staggering solves the
  same problem for the synchronized-firing case (the worst case for CSMA)
  [S901]. pewpew's fixed-rate beacon already rate-limits per node; the storm
  risk is in *event-triggered* rebroadcasts, which must be suppression-gated
  [S910][S901].
- **Oscillator death spirals / non-convergence.** If PCO coupling ε is too
  large, nodes overshoot and never settle; RFA shows convergence requires ε in
  a bounded range and time-to-sync ∝ 1/ε [S901]. Too-large ε plus loss can
  also cause the "dispersive events" RFA observed (brief group scatter up to
  ~0.1 s) [S901]. Mitigation: conservative ε, reachback (apply at period
  boundaries), and a refractory/blackout window after firing so a node is not
  whipsawed by a burst of echoes [S901][S902].
- **Stale-epoch zombies.** A node that was powered off or long-partitioned
  can rejoin advertising an old-but-not-obviously-old epoch and, under naive
  compare, either be ignored forever (if its epoch wrapped past the live one)
  or, worse, override the fleet. Serial-number arithmetic (RFC 1982
  half-range compare) plus the session-ID guard above bounds both failure
  directions [S912]. A monotonic epoch that only ever increases per session,
  never resets on reboot within a session, is the discipline that keeps this
  safe [S912].
- **Split-brain tempo.** Two long-lived partitions can drift to different
  BPMs; on rejoin the max-epoch merge picks one and the PCO phase re-locks,
  but there will be an audible tempo snap. This is inherent to leaderless
  operation and is the accepted cost; it is bounded by how often the host
  re-asserts tempo (each re-assert is a fresh high epoch) [S907][S903].

## Verdicts

Algorithm verdicts use proven / promising / impractical-here.

- **Mirollo–Strogatz pulse-coupled oscillator model — proven.** 35 years of
  theory and multiple hardware implementations; the correct abstraction for
  leaderless beat-phase agreement because it exchanges *events*, not clock
  values [S900][S901][S904].
- **Reachback Firefly Algorithm (staggering + reachback + refractory) —
  proven, and the template to copy.** Demonstrated on real lossy multi-hop
  radios at ~100 µs (µs-class because of MAC timestamps; ms-class expected
  without them, still far inside a beat budget) [S901]. Its three fixes map
  1:1 onto ESP-NOW hazards (CSMA storm on synchronized firing, late/queued
  messages, echo whipsaw) [S901].
- **Stochastic-coupling PCO convergence (Klinglmayr/Bettstetter) — proven for
  our conditions.** Convergence guaranteed on arbitrary connected topologies
  with variable delays *and* unreliable/probabilistic pulses — packet loss is
  part of the proof, not a threat to it [S903].
- **Epidemic/gossip dissemination (anti-entropy + rumor-mongering) — proven,
  and trivially cheap here.** O(log N) rounds; over physical broadcast in one
  domain it collapses to "every beacon carries newest (epoch,value)", which is
  full-state anti-entropy made free by the 11-byte state size [S905][S906].
- **Trickle (RFC 6206) — proven; adopt its suppression + reset semantics, not
  its idle back-off.** Standardized, production-proven in RPL; propagates on
  link-transmission timescales, scales logarithmically with density
  [S910][S911].
- **LWW max-epoch register (state-based CRDT) — proven; the state model to
  use.** Monotone-semilattice merge gives Strong Eventual Consistency under
  loss/reorder/duplication with no coordination, in ~2 bytes [S907]. Pair with
  RFC 1982 serial arithmetic for wrap safety [S912].
- **Lamport clocks — promising, hold in reserve.** Only needed if concurrent
  writers appear (two hosts / on-node UI edits during partition); +1 ID byte
  buys a causal total order [S908]. Version vectors — impractical-here (O(writers)
  bytes blows the 11-byte budget) [S909].
- **Neighbor-state CA as literal synchronous rules (Life-class) —
  impractical-here.** Synchronous-tuned rules cross a phase transition and
  dissolve under the asynchrony/loss pewpew's medium imposes [S913][S914].
- **Gradient/diffusion activation fields (amorphous computing) — proven; the
  right way to do neighbor-propagated waves.** Monotone relay self-heals under
  loss, same convergence guarantee as the epoch merge [S915][S907]; 10 Hz
  inter-group stepping sits in the apparent-motion sweet spot [S916].
- **FPP MultiSync / WLED UDP sync as the tempo mechanism — impractical-here.**
  Both are clock/state *mirroring* that presuppose a master or supply no
  continuous phase; they reintroduce exactly the centralization the mesh tier
  removes [S163][S158].
- **FTSP flooding time-sync — proven but not directly usable on ESP-NOW.**
  µs-class, failure-robust, but requires MAC-layer TX timestamps ESP-NOW does
  not expose to app code; keep as a "if we get firmware access" option
  [S917].
- **GPS/PPS absolute clock — proven; the escape hatch for hard absolute time.**
  ~15–30 ns 1PPS, no radio coordination, at a modest per-node BOM + sky view;
  reach for it only when an install genuinely needs wall-clock-referenced
  action [S918].

### Recommended coordination stack for pewpew's mesh tier

Layered, each layer justified and all riding the same ~11-byte fixed-layout
broadcast at ~10 Hz (no ACKs, no membership, no routing):

**Layer 0 — Membership-free local broadcast.** Every node periodically
broadcasts one fixed-layout ~11-byte frame at ~10 Hz and listens promiscuously;
there is no join, no peer table, no neighbor list. Justification: broadcast
gives one-to-all delivery so gossip and PCO both piggyback on a single
transmission, and membership-free operation is what makes partition/rejoin a
non-event [S905][S903]. (Airtime viability at 25–150 nodes is RA-13's verdict,
not re-litigated here.)

**Layer 1 — Epoch'd parameter state via gossip (the "live playground"
channel).** The frame carries `(session_id, epoch, param_digest/values)`.
Merge rule = lexical max on `(session_id, epoch)` with RFC 1982 wrap-safe
epoch compare — a state-based LWW register, i.e. a CRDT, so every beacon is
also an anti-entropy exchange and every node is an unwitting relay
[S907][S912]. A node hearing a newer epoch may immediately rebroadcast
(Trickle reset), gated by Trickle-style suppression to avoid storms
[S910][S901]. Result: a host-injected parameter edit converges fleet-wide in
~2–3 beacon intervals (~200–400 ms) even at p≈0.2 loss over 50 nodes, with no
central engine — meeting the on-the-fly-editing requirement [S905][S906][S910].
BPM lives here as one of the parameters.

**Layer 2 — Optional firefly phase layer for beat.** A few bytes of the same
frame carry a downbeat phase pulse; nodes run a Mirollo–Strogatz oscillator at
the bar/beat period and nudge phase toward heard pulses using RFA discipline —
random stagger within the period, reachback (apply at period boundary), and a
refractory window — with conservative coupling ε [S900][S901]. Timestamp-free,
so accuracy is bounded by channel jitter (a few ms), which is inaudible against
a ≥300 ms beat; convergence is guaranteed under the loss and topology churn a
mobile outdoor fleet exhibits [S903]. This layer is *optional*: with it off, the
fleet still shares scene/palette/tempo-value/waves via Layer 1; with it on, they
additionally share beat *phase*.

**Layer 2b (waves) — gradient/activation fields, not literal CA.** Spatial
"waves of activity between neighbors" are implemented as monotone
activation/gradient relays over the same neighbor broadcasts, degrading
gracefully under loss and stepping at 10 Hz within the apparent-motion window
[S915][S914][S916].

**Layer 3 — Optional absolute clock, off by default.** Gateway reference ticks
for convenience, or GPS/PPS for installs needing hard wall-clock action; never
required for the core coordinated-autonomy goal [S918][S900].

Every layer is expressible inside a fixed ~11-byte frame (session+epoch ≈ 3 B,
a handful of parameter/palette/tempo bytes, a 1-byte phase/downbeat field, a
1-byte activation/wave field) and none requires per-frame ACK, retransmission,
or knowledge of who the neighbors are — the properties that keep it viable at
~10 Hz across 25–150 autonomous nodes [S907][S903][S910].

## Code-reading queue

Ranked; feeds Phase 2. Per project rules, only algorithm/protocol-level
reference implementations, not hobby art repos.

1. **Contiki-NG / RIOT OS Trickle timer implementation** (`os/net/routing`
   Trickle, or RIOT `sys/trickle`) — read the canonical Imin/Imax/k state
   machine, suppression counter, and reset-on-inconsistency to lift the exact
   parameter discipline for pewpew's Layer-1 rebroadcast gating. Answers: what a
   correct, tested Trickle looks like in C on constrained nodes [S910][S911].
2. **TinyOS FTSP / RFA reference (`tos/lib/ftsp`, and the RFA TinyOS sources
   referenced by [S901])** — read how MAC-layer timestamping and the reachback
   queue are structured, to design the ESP-NOW-analogue (sender-side stagger
   compensation) that survives without MAC timestamps. Answers: minimal PCO
   state machine and what specifically breaks without TX timestamps [S901][S917].
3. **A state-based CRDT LWW-register reference (e.g. an established CRDT
   library's LWW-register)** — confirm the merge/compare edge cases (ties,
   wrap) against RFC 1982 semantics before committing the 2-byte epoch format
   [S907][S912].
4. **ESP-IDF `esp_now` + `esp_timer` / `esp_wifi` TX callback path** — determine
   empirically whether any usable transmit timestamp is exposed (tx-done
   callback timing), which sets the achievable PCO phase floor. Answers the
   central Open question below [S901][S917].

## Open questions

- **Timestamp-free PCO phase floor on ESP-NOW specifically.** The µs-class
  firefly results all use MAC-layer timestamps [S901][S904]; the ms-class claim
  for timestamp-free ESP-NOW is reasoned from RA-13 latency figures, not
  measured. Settled by: a bench test — N ESP32-S3 nodes running staggered
  reachback PCO, logic-analyzer on a GPIO toggled at each node's downbeat,
  measure group spread vs node count and offered load. Also settles whether
  ESP-IDF's tx-done callback gives a usable sender-side timestamp (code read #4).
- **Convergence time of PCO at ESP-NOW parameters and 25–150 nodes.** RFA's
  1/ε scaling and M&S all-to-all convergence are established [S900][S901] but no
  measurement exists at pewpew's node counts, mobility, and 10 Hz cadence.
  Settled by: the same bench test scaled up, or a TOSSIM/ns-3-class simulation
  with an ESP-NOW PHY model.
- **Tyrrell/Auer/Bettstetter details** [S902] are from abstract + secondary
  summaries only (full text 403). The specific delayed-emission/refractory
  parameters and the 30-node convergence-rate curves are [NEEDS-VERIFICATION];
  settled by obtaining the paper.
- **Gradient/CA rule selection for pleasing waves under loss.** The literature
  says synchronous-tuned rules dissolve under asynchrony [S913][S914] and that
  monotone gradient fields are robust [S915], but *which* concrete
  activation-field rules give the most attractive emergent motion at 10 Hz with
  20% loss is an aesthetic/empirical question no source settles. Settled by: a
  simulator sweep in pewpew's own preview harness (RA-11 territory).
- **Interaction of Layer-1 gossip traffic with Layer-2 PCO firing on one
  10 Hz beacon.** Combining epoch gossip, phase pulses, and wave state in a
  single fixed frame is proposed but not validated for airtime/latency
  coupling at scale — cross-references RA-13's airtime verdict; settled by the
  same fleet bench test.
- **Apparent-motion figures** [S916] are drawn from encyclopedic summaries of
  Wertheimer (1912) / Korte (1915); the exact ISI thresholds should be
  confirmed against a modern perception textbook or the primary monographs
  before they anchor a hard design bound [NEEDS-VERIFICATION].
