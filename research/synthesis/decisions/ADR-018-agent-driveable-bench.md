# ADR-018: The agent-driveable lab bench

Status: Proposed (2026-07-10)

## Context

Everything below the radio boundary (ADR-017) needs hardware: ESP-NOW
delivery rates, PCO phase spread, dither photometry, coexistence soaks,
power profiles — §12 maps ten items onto permanent rigs. The bench must be
driveable by CI and by coding agents, because 2026 practice reviews
evidence artifacts from unattended runs rather than supervising sessions,
and because hardware tests that require a human at a desk simply don't get
run. The 2026 literature supplies the interaction patterns (CLI-first,
structured output, statistical gating) but **no worked safety framework for
agents actuating physical hardware** — that boundary is composed here from
adjacent evidence.

## Decision

- **One bench, permanently assembled, on a self-hosted runner** (the
  existing Pi 5/N100 host): ~$200 core — 6× ESP32-S3 devkits,
  uhubctl-verified powered hub (per-port VBUS power-cycling), fx2lafw-class
  logic analyzer + sigrok (mainline WS281x decoder), AR9271 monitor-mode
  WiFi adapter + scapy, TSL257 photodiode jigs; ~$500 tier adds Saleae
  Logic 8 (its 10 MS/s analog channels collapse the protocol and photometry
  rigs onto one instrument) and a Nordic PPK2 (power profiling +
  source-meter). Full BOM with per-item automation paths in RA-19.
- **Software contract: pytest is the bench's API.** pytest-embedded
  (Espressif's own framework; multi-DUT `count`/per-DUT targets is exactly
  the sender-fleet+sniffer shape) + Unity `TEST_CASE_MULTIPLE_DEVICES` for
  two-board protocol checks + pytest-rerunfailures quarantine vocabulary.
  Every instrument is driven from the same Python process; every §12 rig
  item is a test, not a lab afternoon.
- **Known-state discipline**: power-cycle every DUT via uhubctl before
  every run (the board-farm convergent lesson); artifacts captured on
  state-change, not continuously (ring-buffer serial per DUT, pcap + logic
  capture windows on health-trip), uploaded as CI artifacts.
- **Statistical gating, never hard gates**: open-air 2.4 GHz results are
  distributions; bench checks report pass^k over k isolated trials with
  kept transcripts. Sessions hard-gate only on L1/L2 (deterministic) checks.
- **Soaks are daemon-owned, CI-observed**: a bench-host daemon appends
  newline-JSON health records; scheduled workflows (and agents) read the
  latest snapshot and fail loudly on regression. Self-hosted runners are
  also what makes multi-day jobs possible at all (5-day cap vs 6 h hosted).
- **Agent access tiers** (ours to define — the literature is thin):
  - **Tier 0, read-only, always allowed**: serial tails, capture reads,
    telemetry queries, soak-artifact reads.
  - **Tier 1, bench actuation, allowlisted verbs**: flash / power-cycle /
    pattern-push on bench DUTs only; every verb has `--dry-run`; every
    invocation audit-logged; exposed as CLI first, MCP tool server as the
    remote surface (post-2026-07-28 MCP: stateless core + Tasks for
    long-running captures). Namespaces separate read from actuate; the
    permission system, not prompt text, is the enforcement layer.
  - **Tier 2, deployed fleet: read-only, period.** Telemetry-watching
    agents file findings and propose fixes; no unattended actuation of the
    fleet, ever. Gateway-mediated fleet writes happen in attended sessions.
- **Runner security**: private repo (or public-proxy-to-private pattern);
  fork PRs never reach the runner.

## Consequences

- Every permanent §12 rig item becomes `uv run pytest --bench <item>`-class
  invocable — by CI on schedule, by an agent verifying a firmware change,
  by a human before an unattended run. The marginal cost of re-running a
  hardware experiment drops to ~zero, which is the whole point.
- The bench is a single point of failure for L4 feedback; it is also
  fungible commodity hardware (same one-SKU logic as the fleet, ADR-016) —
  spare devkits are fleet spares.
- PPK2's Python API is unofficial (protocol undocumented by Nordic) and
  sigrok's decoder set moves slowly — both are isolated behind the bench's
  own verbs so a breakage is a bench bug, not a test-suite rewrite.
- Open-air RF variance is accepted and handled statistically; anyone
  needing shielded repeatability later adds a chamber, not a redesign.
- The tier boundaries are policy we enforce, not industry standard we
  inherit; they get revisited as the (currently thin) bench-safety
  literature matures.

## Evidence

- [S1115][S1116][S1117] pytest-embedded: Espressif's own CI framework;
  multi-DUT parameterization; the flaky/xfail/temp_skip_ci quarantine
  vocabulary; MIT, active 2026.
- [S1118] Unity TEST_CASE_MULTIPLE_DEVICES (≤5 UART-synced DUTs) — the
  two-board protocol-test primitive (§12 item 19).
- [S1133] uhubctl + verified-hub list ("most hubs lie") — per-port VBUS
  power-cycling; [S1122][S1121] board-farm practice: power-cycle to known
  state before every run; two-repo runner-security pattern.
- [S1120][S1123] Self-hosted runners: USB hardware access, 5-day job cap
  (vs 6 h hosted), 35-day workflow span — what makes soaks CI-adjacent;
  [S1143] scheduled check-in workflows.
- [S1125][S1126][S1127] sigrok-cli headless + mainline WS281x decoder +
  fx2lafw hardware (24 MS/s = 30 samples/WS2812 bit).
- [S1128][S1129][S1130] Saleae Logic 2 official gRPC/Python automation;
  8 digital @100 MS/s + analog @10 MS/s — one instrument for §12 items
  3/5/11/16/17.
- [S1131][S1132] PPK2: 200 nA–1 A @100 kS/s, 0.8–5 V source-meter;
  `ppk2-api-python` automation (unofficial — isolation consequence above).
- [S1135][S1136][S1134] Monitor-mode capture (AR9271/MT7612U mainline) +
  scapy pcap pipelines; ESP32 promiscuous-mode as the RSSI-faithful
  cross-check.
- [S1137] TSL257 + IEEE 1789 flicker metrics — the photometry rig; no
  published LED-dither rig exists (assembly is ours).
- [S1150][S1168] 2026 doctrine: CLI-first structured output, dry-run on
  mutations, evidence artifacts over supervision.
- [S1154][S1170] pass^k over isolated trials + transcript reading;
  statistical flake handling over blind retries.
- [S1159][S1160] MCP revision (stateless core, Tasks extension,
  2026-07-28) — the remote-surface shape; [S1162][S1163][S1161] young
  hardware MCP servers — read for tool-surface shapes, not dependencies.
- [S1155][S1156][S1157] Permission habituation data (93 % approval),
  sandbox + allowlist + classifier layering — why the permission system,
  not prompts, is the enforcement layer.
- [S1171][S1172] Seer model: telemetry-watching agents with human-gated
  actuation — the Tier-2 precedent.

## Rejected alternatives

- **Ad-hoc lab afternoons per §12 item** — unrepeatable, human-gated,
  incompatible with agent verification; the status quo this ADR exists to
  end [S1150].
- **labgrid as the bench framework** — the reference design for
  place/resource modeling, but Linux-SBC-flavored (bootloader/rootfs
  workflows); pytest-embedded already speaks ESP-IDF natively [S1119]
  [S1115]. Steal its resource-model ideas if the bench outgrows one host.
- **Hosted CI runners** — 6 h job cap kills soaks; no USB [S1123][S1120].
- **MCP-wrapping every instrument as the primary interface** — 2026
  guidance is CLI-first for local dev operations; MCP is the remote/
  long-running surface, not the default wrapper [S1150][S1168][S1159].
- **Hard-gating sessions on bench results** — physics flakes would wedge
  agent sessions; statistical gating exists for exactly this [S1154].
- **Depending on existing hardware MCP servers** — 47-star ecosystem,
  single-author projects; shapes yes, dependencies no [S1161][S1162][S1163].
- **RF-shielded chamber now** — cost/complexity for a repeatability
  problem pass^k already absorbs; revisit only if item-15-class results
  stay too noisy to gate on [RA-19].

## Amendment (2026-11-05) — which engines a tier-1 write may reach

ADR-023 gives agents tier-1 verbs that change a running engine: `push`
and the MCP tools `engine_apply` and `engine_set`. The decision above
says what tier 1 may do on the bench; it does not say how a tool tells a
bench engine from a deployed one, and a pewpew engine looks the same on
either. Backlog: `docs/backlog/v0.3.x.md`.

### Decision

- **A tier-1 write goes only to a loopback engine** (`127.0.0.0/8` or
  `::1`, tested with the stdlib's `ipaddress.is_loopback` [S1466]),
  unless the operator passes `--allow-host IP` for a bench machine. The
  flag is per invocation, names one IP address per use and may be
  repeated; there is no wildcard, and a host name is refused, so what it
  allows cannot move with DNS. Every address the engine URL's host
  resolves to must pass, and the client connects to the address it
  checked, never resolving again: the
  websockets client (17.0.1, observed) hands a host name to
  `socket.create_connection`,
  which tries each resolved address in turn [S1469], so a name that
  resolves to loopback and a fleet address would reach the fleet whenever
  nothing listens locally.
- **The engine must also have opted in.** A tier-1 tool writes, a `set`
  included, only to an engine whose `hello` lists the `look` capability,
  which only `run --accept-looks` gives and which `--unattended` refuses
  (ADR-020 amendment "capabilities"). The deployed aura runs on this
  laptop (`deploy/launchd/pewpew-aura.plist`), and `run` accepts `--host
  0.0.0.0` with only a warning, so an aura bound to every interface is
  reachable at `127.0.0.1`; the address test alone would let a write
  through.
- **Any other engine is fleet**, so tier 2: read-only. `observe`,
  `engine_observe` and `fleet_status` may read it; nothing writes to it.
- **The rest of tier 1 holds:** `--dry-run` first (the MCP tools default
  to `dry_run=true`), and an audit record through `pewpew.audit.record`
  before the first byte is sent.
- **Code and permissions enforce it, not the tool description.** The
  address and opt-in checks run in the tool; the MCP server's tier is fixed at
  launch (`--tier 0|1`) and a tier-0 server does not list the write tools;
  the client's permission rules decide whether the tier-1 server runs.

### Consequences

- An agent on the laptop can drive the engine it started for a test with
  `--accept-looks`, and cannot write to the deployed aura on the same
  laptop: it binds the router's address, and bound to every
  interface it still never lists `look`.
- Tests: a host that resolves to a loopback and a non-loopback address is
  refused; the client connects to the checked address; and an engine
  whose hello lacks `look` is refused for `set` as for `look`.
- A bench engine on another machine needs `--allow-host` each time; that
  costs a flag and keeps the default safe.

### Evidence

- [S1466] Python's `ipaddress`: `is_loopback` per RFC 3330 and RFC 2373.
- [S1469] Python's `socket.create_connection` resolves a host name and
  tries "all possible addresses in turn until a connection succeeds".
- [S1155][S1156] The permission system and sandbox, not prompt text, are
  the enforcement layer.
- [S1160] MCP: tool annotations are untrusted unless the server is
  trusted, and a human should be able to deny an invocation.

### Rejected alternatives

- **A host allowlist file.** It drifts from the network it describes, and
  a stale entry turns a fleet engine into a bench engine silently.
- **Trusting a tool's annotations or description** to keep writes off the
  fleet. Annotations are hints a client may not honour [S1160].
- **Asking the engine alone whether it is a bench engine.** The engine
  would vouch for itself; a deployed engine started with the wrong flag would
  accept agent writes. Its opt-in is a second condition beside the address
  test, never the only one.
- **Testing the first resolved address only.** The connection may go to
  a later one [S1469].
