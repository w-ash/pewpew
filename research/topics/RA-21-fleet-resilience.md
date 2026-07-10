# RA-21: Fleet resilience — node survival, forensics, fault injection & field ops

Last researched: 2026-07-09
Status: draft
S-ID block: S1200–S1249

## Key questions

- **Degradation ladder**: what graceful-degradation hierarchies are established
  practice for device fleets (full coordination → standalone render →
  hold-last-state → safe/dark), and who decides transitions — local watchdog or
  gossip liveness? Precedents in show control (DMX hold-last-look) and IoT.
- **Node survival (ESP32-S3)**: task/interrupt watchdog discipline for a 60 fps
  render loop; brownout detector thresholds vs battery sag under TX bursts;
  recovery from a wedged WiFi stack; boot-loop detection → safe-mode firmware;
  NVS write-frequency discipline; should a node self-reboot on anomaly?
- **Black-box forensics**: core-dump-to-flash cost and retrieval;
  `esp_reset_reason` fidelity; crash counters in RTC memory vs NVS;
  panic-→-telemetry-on-next-boot patterns; what a Memfault-class pipeline
  captures, as the design reference.
- **Chaos/fault injection**: what does fault injection for embedded fleets look
  like in practice (RF interference, programmable-supply brownout, node-kill
  drills, sim packet loss), and how do server-side chaos principles
  (steady-state hypothesis, blast radius) translate? How thin is the literature?
- **Canary & staged rollout**: rollout-ring practice and automatic rollback
  triggers at fleet scale; how tens-of-nodes fleets adapt techniques built for
  millions; version-skew tolerance as a protocol requirement.
- **Field operations**: spares math for a 50-node fleet; failure-rate priors
  for ESP32-class hardware; connector/strain-relief/potting wisdom from outdoor
  LED practice; pre-event burn-in; swap-don't-debug policy.
- **Environmental stress**: thermal derating in sun-heated enclosures, battery
  capacity vs temperature, conformal coating vs potting.

## Findings

Scope note: ADR-015 (leaderless epoch gossip, partition-as-non-event) and
ADR-016 (dual-slot OTA + rollback, version telemetry, windowed updates, node
fungibility) fix the fleet-level primitives. This doc covers what they assume
but do not specify: what a single node does to survive, what it records when
it dies, how we practice failure, how new firmware is admitted to the fleet,
and how the fleet is operated in the field.

### 1. The degradation ladder — precedents and who decides

**Stage lighting has a 30-year-old convention for exactly this problem.**
DMX512 receivers losing their control signal do not go dark; they hold. A
representative device manual states it plainly: "The Converter is designed to
hold the last levels received from the console in the event the DMX512 signal
is lost. These levels will be held until control is restored or power is
removed" [S1223]. Two details of the convention matter as much as the hold
itself: (a) blackout-on-loss exists but is the *opt-in* behavior (a jumper
labeled "REMOVE JUMPER TO BLACK-OUT ON LOSS OF SIGNAL", taking effect ~1 s
after loss) [S1223]; and (b) hold does not survive power: "All levels are
reset to zero upon power up" [S1223]. Stale show state is held through a
*signal* interruption but never replayed across a *power* interruption — a
distinction pewpew should copy (hold parameters through radio silence; boot
into a neutral default, not the last look, after a reset).

**The networked successor codifies the decision mechanism: a local timer.**
ANSI E1.31 (sACN) defines network data loss as either 2.5 s of silence from a
source (`E131_NETWORK_DATA_LOSS_TIMEOUT`) or receipt of the stream-terminated
option bit, which a source shutting down cleanly sends three times [S1224].
The receiver decides alone, on its own clock; there is no consensus round and
no third party. What the receiver *does* on loss (hold, fade, blackout) is
left to the implementation — the standard specifies detection, not response
[S1224]. This is precisely the shape ADR-015 already gives pewpew: partition
is detected locally (beacons stop arriving) and tolerated locally (the CRDT
state simply stops updating), so the "who decides" question has a
show-control-blessed answer: **each node's local timers and watchdogs decide;
gossip liveness only informs which rung the node renders from, never whether
the node survives** [S1224][ADR-015].

**IoT fleet practice adds the bottom rungs.** Where show control degrades
from *coordinated* to *autonomous-hold*, device-fleet practice degrades from
*running* to *minimal-but-reachable*: ESPHome's safe mode boots a firmware
image in which "all components are disabled except serial logging, network
(Wi-Fi or Ethernet) and the OTA component(s)" after repeated boot failures
[S1210], and Memfault's reboot classification separates expected reboots
(user- or update-initiated) from unexpected ones so a fleet dashboard can see
a regression as a spike [S1213]. Combining the two traditions gives pewpew a
four-rung ladder, each rung locally decided:

| Rung | State | Entered by (local decision) |
|---|---|---|
| L0 | Coordinated: gossip fresh, rendering group state | beacons arriving; epochs advancing [ADR-015] |
| L1 | Autonomous: rendering last-known parameters, local clock free-runs | beacon silence past a 2.5 s-class timeout, sACN-style [S1224] |
| L2 | Hold/neutral: render a safe default scene (dim, static) | reboot (never replay stale look across reset [S1223]); or repeated internal faults short of boot-loop |
| L3 | Safe mode: minimal firmware, radio listening for OTA only, LEDs dark or status-dim | boot-loop counter threshold, ESPHome-style [S1210] |

L0↔L1 transitions are non-events by design (ADR-015); L2 and L3 are
node-health rungs, not coordination rungs — a node at L3 is visible to the
fleet only through its absent/degraded telemetry [ADR-016].

### 2. Node survival mechanics (ESP32-S3 specifics)

**Watchdog configuration discipline.** ESP-IDF ships three relevant
watchdogs, all enabled or enableable by Kconfig [S1200]:

- The **Interrupt Watchdog (IWDT)** (`CONFIG_ESP_INT_WDT`, default on)
  catches ISRs/critical sections that block the CPU past
  `CONFIG_ESP_INT_WDT_TIMEOUT_MS`; its timeout must be at least twice the
  FreeRTOS tick period, and it panics on expiry [S1200][S1201]. For pewpew
  this is the backstop against exactly the class of failure RA-16 worries
  about — RMT/DMA/radio ISR interactions wedging a core.
- The **Task Watchdog (TWDT)** (`CONFIG_ESP_TASK_WDT_EN`, default on) watches
  the idle tasks of both CPUs by default; application tasks opt in with
  `esp_task_wdt_add()` and must call `esp_task_wdt_reset()` within
  `CONFIG_ESP_TASK_WDT_TIMEOUT_S` [S1200]. Critical default: on expiry the
  TWDT "simply print[s] a warning and a backtrace" — it does **not** reset
  the node unless `CONFIG_ESP_TASK_WDT_PANIC` is set [S1200]. A fleet whose
  design stance is "reboot, don't wedge" must flip that option; a printed
  warning on a dark hillside helps no one.
- The **RTC watchdog** guards the boot path
  (`CONFIG_BOOTLOADER_WDT_ENABLE`, default on, 9 s) and is re-armed to 10 s
  inside the panic handler itself, so even a crash *in the crash handler*
  ends in a reset rather than a hang [S1201].

Industry best practice layers a *software* watchdog under the hardware one:
feed the hardware watchdog from a dedicated low-priority task — "A low
priority thread. If it's able to run, we'll feed the watchdog. If a task gets
starved or something higher priority is stuck in a loop, the system should
reboot" — and gate that feed on every registered task having checked in,
never feeding from a timer ISR (which keeps running while the system it
vouches for is dead) [S1215]. Hardware timeouts of 5–30 s with the
state-capturing software watchdog set slightly shorter are the recommended
shape [S1215]. Mapping to pewpew: the 60 fps render task, the ESP-NOW RX
handler, and the telemetry task each subscribe to the TWDT; the render task
resets it once per frame batch (not per frame — a 1 s-class TWDT timeout
gives ~60 frames of margin and keeps the reset call out of the hot path).

**The wedged-radio case needs its own supervisor.** The default watchdogs do
not cover the WiFi/radio stack's internal tasks: Espressif's own tracker
documents the stack getting stuck during connection with no watchdog firing
[S1209]. Since a pewpew node's radio liveness is directly observable — at
10 Hz beacon rates, *hearing nothing for several seconds while peers exist*
is an anomaly — the correct supervisor is an application-level RX-silence
timer: on expiry, tear down and re-init the radio path; if that fails or
recurs, escalate to `esp_restart()` and let boot-loop accounting take over
[S1209][S1215]. This is the same local-timer shape as the L0→L1 ladder
transition, applied one layer down.

**Brownout vs battery sag.** The S3's brownout detector is on by default and
resets the chip when the rail sags below a configurable threshold; the
default level is `ESP_BROWNOUT_DET_LVL_SEL_7` ≈ 2.44 V, with selectable
levels up to 3.30 V — and Espressif's own Kconfig carries the caveat that
"the voltage levels here are estimates" with chip-to-chip variation
[S1206:components/esp_hw_support/power_supply/port/esp32s3/Kconfig.power#L16-L39].
On brownout the chip prints "Brownout detector was triggered" and resets —
and if the rail is collapsing fast, "only part of the message may be seen"
[S1201]. Two fleet consequences: (a) radio TX bursts are the load spikes most
likely to sag a tired battery, so `ESP_RST_BROWNOUT` counts in telemetry are
*battery-health signal*, not just crash noise [S1204]; (b) cold multiplies
the risk — lithium cells deliver roughly half their rated capacity at –18 °C
and their internal resistance rises, deepening sag under load [S1225]. A
node brownout-looping at dusk in winter is a battery event, and the reset
telemetry should make that legible without a ladder climb [S1204][S1213].

**Boot-loop detection → safe mode.** The production-proven pattern is
ESPHome's: count consecutive failed boots; after a threshold (default 10)
boot a minimal image — network + OTA only, everything else disabled; a boot
counts as good after surviving a period (default 1 min); safe mode itself
reboots after `reboot_timeout` (default 5 min) to retry the real firmware
[S1210]. One documented sharp edge: a crash that happens *before the counter
increments* (during early component setup) defeats the count entirely, and
devices have boot-looped for 15+ minutes without ever reaching safe mode
[S1211]. The lesson for pewpew: increment the counter at the earliest
possible point in `app_main` (before subsystem init), not after setup
succeeds — and remember the IDF dual-slot rollback (ADR-016 [S1003]) already
covers the *new-firmware-is-bad* case; the safe-mode counter covers the
*old-firmware-meets-new-world* case (corrupt NVS, failing hardware, hostile
RF).

**NVS write discipline.** NVS is log-structured: updates append rather than
overwrite, which "reduces the frequency of flash erase to flash write
operations for data types fitting one entry by a factor of 126", and the
design guarantees power-off at any moment costs at most the in-flight
key-value pair [S1205]. Underlying module flash endures 100,000
program/erase cycles [S1207]. For pewpew's write pattern — config at
provisioning, scene defaults occasionally, counters once per boot — wear is
a non-issue at three orders of magnitude of margin; the discipline is simply
**never write NVS per-frame or per-beacon**, and on battery hardware enable
`CONFIG_NVS_FLASH_VERIFY_ERASE`, which exists precisely because unstable
supplies can corrupt erase operations [S1205]. High-frequency state that
must survive a *reset* (not power loss) belongs in RTC noinit RAM instead
(§3) [S1208].

**Should a node self-reboot on anomaly? Yes — with forensics first.** The
academic case is crash-only software: systems with exactly one way to stop
(crash) and one way to come up (recover) end up more reliable than systems
that try to shut down gracefully, because the recovery path is the
always-exercised path [S1222]. Embedded practice agrees: devices should
always reboot rather than remain wedged, with the software-watchdog stage
existing to capture state *before* the reset [S1215]. Memfault's design
closes the loop: record the reason (software-marked if known, hardware reset
register otherwise), classify expected vs unexpected, and alarm on
fleet-wide spikes — a reboot that is recorded is recovery; a reboot that is
not is a mystery [S1213]. The one hazard is reboot *loops*, and that is what
the boot-loop counter → safe-mode rung is for [S1210].

### 3. Black-box forensics

**Core-dump-to-flash is the flight recorder, and it is cheap.** ESP-IDF can
write an ELF-format core dump to a dedicated flash partition on any panic:
task snapshots (TCBs + stacks), crashed-task registers, panic reason,
optionally `.bss`/`.data`/heap via `CONFIG_ESP_COREDUMP_CAPTURE_DRAM`, with a
SHA256 integrity checksum; the conventional partition is 64 KB (`type: data,
subtype: coredump`), with a documented minimum of
`20 + (max tasks × (12 + TCB size + max stack size))` bytes and
`CONFIG_ESP_COREDUMP_MAX_TASKS_NUM` to bound it [S1202]. Against pewpew's
8–16 MB module flash, 64 KB is noise. Retrieval does not require a bench:
the espcoredump component exposes a runtime API — `esp_core_dump_image_check()`
/ `esp_core_dump_image_get()` to find and read the stored image,
`esp_core_dump_get_summary()` for a compact struct with the crashed task's
backtrace and exception info, `esp_core_dump_get_panic_reason()` for the
reason string, and `esp_core_dump_image_erase()` after upload
[S1203:components/espcoredump/include/esp_core_dump.h#L96-L162]. That is the
technical basis for a "dead node tells the gateway what killed it at the next
maintenance window" workflow; full-image transfer wants the OTA-window WiFi
path (ADR-016), while the *summary* is small enough to consider for normal
telemetry.

**Reset-reason introspection is fleet triage, not just debugging.**
`esp_reset_reason()` distinguishes power-on, external pin, `esp_restart()`,
panic, interrupt-WDT, task-WDT, other WDT, deep-sleep exit, brownout, USB,
JTAG, eFuse error, power glitch, and CPU lockup [S1204]. The
device-observability industry's refinement (Memfault, offered here as design
reference, not dependency) is a two-source model: a *software-marked* reason
recorded before an intentional or anticipated reset takes precedence over
the *hardware register* read on the next boot; the hardware reason "should
clear the reboot reason from the hardware before completing" so each boot
attributes exactly one cause; storage is "a noinit region of RAM" that
survives warm resets [S1213]. Reasons are then classified expected
(user/update) vs unexpected (crash class), and the unexpected-reboot count
becomes the fleet-stability metric that surfaces bootloops and bad releases
[S1213]. Memfault's coredump pipeline adds the operational detail worth
copying: capture is bounded and region-selective when RAM/flash is tight,
upload happens on next boot, and "if coredump saving fails … the system
falls back to recording a simplified trace event capturing only the current
and previous stack frames" — the forensics path itself degrades gracefully
[S1212].

**Crash counters: RTC noinit for the loop, NVS for the lifetime.** ESP32
RTC noinit memory (`RTC_NOINIT_ATTR`) persists across software resets,
watchdog resets, and panics, but is lost on power removal and brownout, and
firmware must gate initialization on reset reason (zero it only on
power-on-class resets) [S1208]. That makes it the right home for the
boot-loop counter and last-panic breadcrumbs (fast, unlimited writes, exactly
the reset classes a loop involves), while NVS — one write per boot at 100k
endurance [S1205][S1207] — holds lifetime odometry: total boots, total
unexpected resets, last-known battery state. This split mirrors both the
ESPHome counter design [S1210] and the Memfault noinit tracking region
[S1213].

**The pewpew forensics minimum** (assembled from the above): every node (a)
core-dumps to a 64 KB flash partition [S1202]; (b) records reset reason with
the two-source discipline [S1204][S1213]; (c) keeps boot/crash counters in
RTC noinit + NVS [S1208][S1205]; (d) carries in its periodic status beacon
(ADR-016 uplink): firmware version, last reset reason, boot count, unexpected
reset count, minimum-ever free heap (`esp_get_minimum_free_heap_size()` —
one call, high diagnostic value for slow leaks [S1204]), battery/rail state;
and (e) answers a gateway "send core dump" command during maintenance
windows [S1203]. This is a strict subset of what a Memfault-class pipeline
captures (coredump + reboot reasons + metrics timeline) [S1212][S1213], so
adopting the vendor later remains open.

### 4. Chaos and fault injection for embedded fleets

**The server-side principles translate; the tooling does not.** Chaos
engineering is "the discipline of experimenting on a system in order to
build confidence in the system's capability to withstand turbulent
conditions in production", built on a measurable steady-state hypothesis,
real-world fault variables, and minimized blast radius [S1220]. The honest
state of the embedded side: a 2024 ICCS paper introducing µChaos (an
open-source fault-injection component for Zephyr OS) surveys the field and
finds mature tools for cloud (Chaos Monkey, Gremlin, Chaos Mesh) but "there
are few known solutions for IoT end devices", those few working mainly in
static software testing or at the MQTT-broker layer [S1221]. µChaos itself
injects CPU, memory, network, sensor, and application faults via a serial
API — but it is Zephyr-only; nothing equivalent ships for ESP-IDF [S1221].
Conclusion: pewpew gets chaos *principles* from the literature and must
build chaos *mechanics* itself (which RA-19's sim/HIL loops are positioned
to host).

**What a 50-node fleet's chaos practice actually looks like.** Adapting
[S1220] to this system, with pewpew-specific steady-state hypotheses drawn
from ADR-015's claims (they are falsifiable predictions — that is what makes
them chaos-testable):

- *Packet-loss injection in sim*: drop 20–50 % of beacons in the RA-19
  simulation; hypothesis: parameter convergence stays ~2–3 beacon intervals
  at 20 % loss (ADR-015). Cheapest experiment, fully automatable [S1220].
- *Node-kill and partition drills* (bench or pre-show): power off random
  nodes / split the fleet with distance or shielding; hypothesis: survivors
  never leave L0/L1, rejoin converges on max-epoch without operator action
  (ADR-015). This is the "vary real-world events" axis — hardware death is
  the event the owner's design stance names [S1220].
- *Brownout injection*: run a node from a programmable supply, sag the rail
  during TX; hypothesis: clean `ESP_RST_BROWNOUT` recording, no NVS
  corruption (with `CONFIG_NVS_FLASH_VERIFY_ERASE` on), rejoin at L0 within
  seconds [S1206][S1205][S1204].
- *RF interference*: saturate the channel with ordinary co-channel WiFi
  traffic (a legal, realistic jammer); hypothesis: degraded convergence but
  no L2/L3 transitions — loss stretches, never breaks, the gossip (ADR-015).
  Note deliberate RF *jamming* proper is regulated; co-channel traffic
  achieves the loss profile without the legal problem
  [NEEDS-VERIFICATION — loss-profile equivalence asserted from RA-13
  contention findings, not measured].
- *Boot-loop / safe-mode drill*: flash a deliberately crashing image to one
  canary node; hypothesis: ≤10 boots to safe mode, node recoverable OTA
  without ladder access [S1210].

Blast radius at fleet scale 25–150 is managed the same way Google sizes
canaries — large enough to detect, small enough to tolerate [S1216]: drills
run on the bench cluster or on ≤10 % of fixtures during pre-show soak,
never mid-show. "Run in production carefully" translates to: the pre-event
soak *is* the production experiment window [S1220].

### 5. Canary and staged rollout at 25–150 nodes

**The big-fleet machinery, for reference.** AWS IoT Jobs deploys with
exponential rollout rates (a base rate per minute that doubles as
success-count thresholds are met) plus an abort configuration that cancels
the job when a threshold percentage of devices reject, fail, or time out —
explicitly to "avoid a bad update from being sent to an entire fleet"
[S1217]. Memfault structures the same idea as cohorts + percentage-staged
rollouts ("a random subset of its devices (amounting to the selected rollout
percentage) will be marked as staged") with fleet-health charts comparing
crash/reboot telemetry across versions as the halt/abort signal [S1214].
Golioth ships cohort-targeted releases behind a rollout toggle (stage, then
notify on enable; disable to stop advertising the release) [S1219].

**The small-fleet adaptation is device pinning, not percentages.** At N=50,
"5 % canary" is 2.5 nodes; percentage machinery degenerates. balena's
answer, built for exactly this scale of fleet, is per-device release
pinning: devices track the fleet release by default, and you pin specific
devices "for example, a development device or when performing a canary
deployment" [S1218]. Google's canary guidance supports the same shrink:
small canary populations reliably detect gross failures (crashes,
bootloops); subtle regressions need larger populations or longer evaluation
windows — so a small fleet substitutes *time* for *population* [S1216].
Canary evaluation should use few, stack-ranked metrics that indicate real
user-visible problems [S1216]; for pewpew those are exactly the forensics
beacon fields: unexpected-reset count, min-free-heap, beacon RX rate, render
health.

**Automatic rollback is per-node; halt is fleet-level.** pewpew already has
the strongest automatic trigger in the right place: IDF dual-slot rollback
reverts a node that fails to mark the new image valid — crash-before-valid
means automatic return to the old slot, per node, no infrastructure (ADR-016
[S1003]). The fleet-level analogue of AWS abort criteria [S1217] is
necessarily human-in-the-loop here (windowed OTA, ADR-016): promotion from
ring to ring is gated on telemetry, and the gate rule at canary size ~5 is
*any* unexpected reset within the soak window blocks promotion (one node is
already 20 % — far past any sane abort threshold [S1217][S1216]).

**Rings for pewpew** (adapting [S1216][S1217][S1218][S1214]):

| Ring | Population | Promotion gate |
|---|---|---|
| R0 bench | 2–5 nodes on the desk / HIL rig (RA-19) | tests + a soak with fault drills (§4) |
| R1 canary | ~5 fixtures (≥1 of each hardware/battery variant), pinned balena-style [S1218] | ≥1 full duty cycle (an evening's show or 24 h soak) with zero unexpected resets, version telemetry confirming the image [S1013] |
| R2 fleet | remaining nodes in the next maintenance window [ADR-016] | version telemetry shows convergence; stragglers visible by version field, chased individually |

**Version skew is a standing condition, not an anomaly.** Staged rollout
*means* the fleet runs mixed versions for hours-to-days (that is the point
of cohorts and rings [S1214][S1217]), and windowed OTA guarantees stragglers
(ADR-016 expects a "version-skewed fleet … transiently"). The design
requirement this places on the mesh protocol: the ADR-014 fixed-layout frame
must carry an explicit protocol/schema version and evolve additively, so an
R1 canary speaks with an R2 fleet during every single rollout. This is a
requirement RA-21 hands to the protocol spec rather than new evidence —
flagged in ADR-014/015 terms [ADR-015].

### 6. Field operations

**Spares math: the method is settled; the failure-rate prior is not.** The
standard approach is Poisson provisioning, per the USAF Rome Laboratory
Reliability Engineer's Toolkit lineage: given population n, per-unit failure
rate λ, and a resupply interval t, "the Poisson distribution can be used to
predict the number of failures that will occur, with a certain probability
(or confidence), and thus the number of depot spares required", choosing the
smallest s with P(X ≤ s) ≥ confidence, typically 90–95 % [S1228]. The
honest gap: **no published field failure-rate prior for ESP32-class fixture
hardware was found this pass** — consumer-module MTBF data is not public,
and fixture failures are dominated by connectors, wiring, and waterproofing,
not silicon [S1229][open questions]. Worked example with an *assumed* prior
(stated as assumption, not finding): if a season is 200 h/fixture and the
per-fixture failure probability per season is 2–5 % (connector-dominated
guess), expected failures at N=50 are λnt ≈ 1–2.5; Poisson at 95 %
confidence gives **s = 4–6 complete spare fixtures** — order 10 % of fleet.
Node fungibility makes a complete-fixture spare pool rational: identity is
the eFuse MAC and config lives in NVS, so a spare becomes any dead node by
re-provisioning, not by bench surgery (ADR-016 [S1011][S1010]).

**Swap-don't-debug is the enabled policy.** Because any spare can assume any
role [S1011], and because the dead node carries its own black box (core dump
in flash, counters in NVS — flash contents survive the swap) [S1202][S1205],
the field procedure is: swap the fixture, bag and tag the corpse, read the
core dump on the bench later [S1203]. Field debugging under show pressure is
how second faults happen; the crash-only stance applies to operations too
[S1222].

**Connectors, strain relief, waterproofing — where fixtures actually die.**
Professional outdoor-pixel practice (Advatek, representative of the
installed-LED industry): IP67 screw-lock connectors with gold-plated pins,
screwed fully home; every extension in-line waterproof-rated; and the
documented failure mode worth quoting — poor waterproofing lets rain short
the supply rail onto data lines, killing controllers and pixels downstream
[S1229]. Their wiring rule (≤15 m controller-to-first-pixel) is a data-
integrity limit that doubles as a keep-the-loom-short discipline [S1229].
For a battery fixture the analogous kill paths are the battery connector
and the LED pigtail; both want strain relief at the enclosure gland and
drip-loop dressing so water tracks away from the entry
[S1229][NEEDS-VERIFICATION — drip-loop specifics are trade practice not
found in a citable doc this pass].

**Pre-event burn-in.** Burn-in exists to truncate the bathtub curve's
infant-mortality region: run assemblies under elevated stress so
manufacturing-defect units fail on the bench, not in the field; typical
regimes are 8–48 h for consumer electronics, up to 168 h for
high-reliability product, static or dynamic (running real workload) [S1227].
pewpew's cheap adaptation: every new or repaired fixture runs a **24–48 h
dynamic soak** — real firmware, real animation, radio on, outdoors or
thermally cycled if possible — before it is show-eligible, with the burn-in
doubling as the R0/R1 soak window (§5) [S1227][S1216].

### 7. Environmental stress (brief)

- **Thermal.** S3 modules are rated –40 to 85 °C ambient [S1207], but a
  sealed dark enclosure in direct sun adds solar gain on top of LED-driver
  and regulator dissipation; the derating question is enclosure-interior
  temperature vs that 85 °C line, plus battery cycle-life loss which begins
  well below silicon limits — lithium cycle life drops ~20 % at 30 °C and
  ~50 % at 45 °C sustained [S1225][NEEDS-VERIFICATION — solar-gain interior
  deltas need a measurement or an enclosure-vendor source; not found this
  pass]. Light-colored enclosures, shading, and mounting off hot surfaces
  are the zero-cost mitigations.
- **Cold.** Capacity ≈50 % at –18 °C with elevated internal resistance
  [S1225] — runtime halves *and* brownout margin shrinks (§2) in the same
  conditions; winter events need battery headroom sized on the cold curve,
  not the datasheet Ah.
- **Coating vs potting.** Conformal coating (25–75 µm) protects against
  humidity/condensation/splash, keeps boards inspectable and reworkable, and
  is thermally benign; potting seals to IP67/68 and adds vibration immunity
  but is heavy, hot, near-impossible to rework, and thermal-cycling stress
  from the encapsulant can itself fatigue solder joints [S1226]. For a
  serviceable fleet built on swap-don't-debug, the right split is: IP-rated
  enclosure + conformal-coated boards for controllers; reserve potting for
  connector backshells and genuinely sacrificial assemblies [S1226][S1229].

### 8. Recommended resilience policy sketch

1. **Degradation ladder** — four rungs, all transitions decided by local
   timers/watchdogs: L0 coordinated → L1 autonomous on ~2.5 s beacon
   silence (sACN-style timeout [S1224]) → L2 neutral default scene after
   any reset (DMX power-up rule: never replay stale looks [S1223]) → L3
   safe-mode firmware after ~10 failed boots (ESPHome pattern, counter
   incremented first thing in app_main [S1210][S1211]). Gossip liveness
   moves nodes between L0/L1 only [ADR-015].
2. **Watchdog stance** — IWDT on (default); TWDT on with
   `CONFIG_ESP_TASK_WDT_PANIC=y` and render/RX/telemetry tasks subscribed
   [S1200]; feed from task context, never timer ISRs [S1215]; bootloader RTC
   WDT on [S1201]; application-level RX-silence supervisor for the radio
   stack with radio re-init → `esp_restart()` escalation [S1209]. Reboot on
   anomaly is policy, wedging is the failure [S1222][S1215].
3. **Forensics minimum** — 64 KB coredump partition + ELF dumps [S1202];
   two-source reset-reason recording, cleared-on-read [S1204][S1213];
   boot/crash counters in RTC noinit, lifetime counters one-write-per-boot
   in NVS [S1208][S1205]; status beacon carries version, last reset reason,
   unexpected-reset count, min-free-heap, battery [S1213][ADR-016]; core
   dumps retrievable over the wire in maintenance windows via the
   espcoredump runtime API [S1203].
4. **Rollout rings** — R0 bench (2–5, HIL + fault drills) → R1 canary (~5
   pinned fixtures, one full duty cycle, zero unexpected resets to promote
   [S1218][S1216]) → R2 fleet in a maintenance window [ADR-016]; per-node
   automatic rollback via dual-slot OTA [S1003]; fleet-level halt is
   human-on-telemetry (percentage abort thresholds are meaningless at N≈5
   [S1217]); protocol frames version-tagged because rings guarantee mixed
   versions [S1214].
5. **Chaos drills** — steady-state hypotheses taken from ADR-015's
   convergence claims; packet-loss in sim, node-kill/partition and
   boot-loop drills on the bench, brownout via programmable supply,
   co-channel traffic as the interference proxy; drills run in pre-show
   soak, never mid-show (blast radius) [S1220][S1221][S1206].
6. **Burn-in + spares** — 24–48 h dynamic soak for every new/repaired
   fixture before show eligibility [S1227]; Poisson provisioning at 95 %
   fill on an assumed 2–5 %/season fixture failure rate → **4–6 complete
   spares per 50 nodes**, revised annually from own fleet telemetry
   [S1228]; swap-don't-debug in the field, corpses to the bench with their
   black boxes [S1222][S1203]; IP67 screw-lock connectors, strain relief at
   glands, coat-don't-pot controllers [S1229][S1226].

## Verdicts

- **ESP-IDF survival machinery (IWDT/TWDT/RTC-WDT, panic handler, brownout
  detector, coredump-to-flash, NVS)** — **stable**: first-party, documented,
  shipped by default across IDF 5/6; the work is configuration discipline,
  not adoption risk [S1200][S1201][S1202][S1205][S1206].
- **Memfault-class device observability practice (reboot-reason two-source
  model, expected/unexpected classification, coredump-upload-on-boot)** —
  **ascendant / proven**: an entire commercial category now exists around
  it; pewpew implements the pattern, vendor adoption stays optional
  [S1212][S1213].
- **ESPHome-style safe mode (boot-counter → minimal firmware)** — **proven**
  pattern with a known implementation trap (count before setup, not after)
  [S1210][S1211].
- **Crash-only / reboot-on-anomaly** — **proven**: 20+ years of academic and
  embedded-practice agreement; the caveats (record first, loop-guard) are
  engineering, not controversy [S1222][S1215][S1213].
- **Staged rollout with cohorts/rings** — **proven**, with the small-fleet
  adaptation being device pinning + time-based soak rather than percentage
  gates [S1214][S1216][S1217][S1218][S1219].
- **Embedded chaos-engineering tooling** — **promising / immature**: the
  principles port cleanly, but tooling is nascent (µChaos is Zephyr-only;
  nothing for ESP-IDF); pewpew must build its drills into RA-19's sim/HIL
  loops. Practicing chaos: **proven**; buying it: **impractical-here**
  [S1220][S1221].
- **Potting node electronics** — **impractical-here**: destroys the
  serviceability that swap-don't-debug and spares math depend on; IP
  enclosures + conformal coating is the stable practice for this fleet
  [S1226][S1229].

## Code-reading queue

1. **espressif/esp-idf — `components/espcoredump/`** (Apache-2.0, active):
   implementation behind [S1203] — summary struct size on Xtensa, image_get
   chunked-read ergonomics, behavior when the partition holds a dump from an
   older firmware version. Feeds the forensics-minimum implementation.
2. **esphome/esphome — `components/safe_mode/safe_mode.cpp`** (GPLv3
   component code): exact counter storage (RTC vs flash preferences),
   increment timing relative to component setup — verify the [S1211] gap and
   design pewpew's counter placement against it.
3. **memfault/memfault-firmware-sdk — `ports/esp_idf/` + reboot tracking
   core** (permissive SDK license, active): the noinit region layout,
   two-source reason merge, and coredump-storage fallback [S1212][S1213] —
   read as reference architecture even if never linked.
4. **espressif/esp-idf — TWDT implementation
   (`components/esp_system/task_wdt/`)**: what actually happens on timeout
   with PANIC set when the wedged task holds a spinlock the panic handler
   wants; informs whether the RX-silence supervisor needs its own core
   affinity [S1200][S1201].

## Open questions

- **ESP32-class field failure-rate priors**: no published fixture-level or
  module-level field failure rates found from any credible source; the
  2–5 %/season spares assumption is a guess. Settled by: pewpew's own
  telemetry after one season (boot counters + swap log make the fleet its
  own actuary) [S1228].
- **Actual S3 brownout thresholds vs battery sag under TX bursts**:
  Espressif's Kconfig says its own voltage labels are estimates [S1206];
  whether default level 7 (~2.44 V) fires before the radio corrupts state on
  a sagging pack is a bench measurement (programmable supply, §4 drill).
- **Core-dump summary over the mesh**: `esp_core_dump_summary_t` size and
  whether a truncated backtrace fits ESP-NOW-scale payloads or must wait for
  the OTA window — needs the espcoredump code read + a measurement [S1203].
- **TWDT-panic during a live show**: panic-and-reboot costs ~seconds of
  darkness on one fixture; print-and-continue risks a zombie. The policy
  chosen here (panic) follows [S1215][S1222], but a mid-show A/B on the
  bench cluster would make the cost concrete.
- **Hold-vs-fade convention beyond one vendor**: E1.31 defines loss
  *detection* only [S1224]; hold-last-look is documented per-vendor
  [S1223]. A wider sweep of fixture/receiver manuals (ETC, Pathway) would
  confirm hold-then-configurable is universal before citing it as "the"
  convention in an ADR.
- **Enclosure solar gain numbers**: interior-vs-ambient temperature deltas
  for small sealed enclosures in direct sun — trade folklore says
  +15–30 °C, no citable source found this pass; settle with a logged summer
  measurement [S1207][S1225].
- **Co-channel-traffic ≈ jamming equivalence**: the §4 interference drill
  assumes contention reproduces the loss profile of hostile interference
  well enough for resilience testing; plausible from RA-13's contention
  data, unproven as equivalence.
