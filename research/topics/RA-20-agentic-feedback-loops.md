# RA-20: Agentic feedback loops

Last researched: 2026-07-09
Status: draft
S-ID block: S1150–S1199

Scope note: RA-11 covers the *human* dev loop (preview, hot-reload); RA-19 covers
the embedded test substrate (sim/emulation/HIL) itself. This doc covers how, as
of mid-2026, production teams give *coding agents* fast, trustworthy, verifiable
feedback at every level — and what that means for a system whose development
will largely be done by Claude Code-class agents against sims, benches, and a
deployed LED fleet.

Freshness discipline: this is the freshness-critical doc of the pass. Every
major practice below is tagged **CURRENT** (2026 evidence), **CARRIED-FORWARD**
(pre-2026 but still endorsed by 2026 sources), or **STALE** (superseded — with
what replaced it). Claims resting only on ≤2025 sources are tagged
`[NEEDS-VERIFICATION — freshness]`.

## Key questions

- What is the mid-2026 norm for "the agent must be able to run and verify the
  change", and how do teams encode it in repo config (CLAUDE.md/AGENTS.md,
  skills, hooks, allowlisted commands)?
- Is "everything as a scriptable CLI with structured output" a real consensus,
  and what do machine-triageable failure artifacts look like?
- What is the 2026 state of exposing lab instruments, serial consoles, and
  fleet telemetry to agents via MCP-class servers? Read-only vs actuating norms?
- Do teams have agents iterate against deterministic simulation and escalate to
  hardware only for confirmation? How are determinism/reproducibility treated?
- What are the current shapes for long-running/background agents, subagent
  fan-out, and adversarial verification?
- What do 2026 sources actually recommend for safety tiers when agents drive
  physical hardware — and where is the literature simply thin?
- Are eval-style, statistically-gated regression harnesses an established
  pattern for noisy (hardware) system behaviors?
- Which 2024–2025 agentic-coding patterns are now considered outdated?

## Findings

### 1. Verification-first agent workflows — the closed loop is the headline practice

**Status: CURRENT (2026).** Anthropic's official Claude Code best-practices doc
(current as of 2026-07) leads its practice list with "Give Claude a way to
verify its work": "Give Claude a check it can run: tests, a build, a screenshot
to compare. It's the difference between a session you watch and one you walk
away from" [S1150]. The stated mechanism is exactly the closed loop pewpew
needs: "Give Claude something that produces a pass or fail, and the loop closes
on its own. Claude does the work, runs the check, reads the result, and
iterates until the check passes" [S1150]. A check is "anything that returns a
signal Claude can read in the conversation: a test suite, a build exit code, a
linter, a script that diffs output against a fixture, or a browser screenshot
compared against a design" [S1150].

As of 2026-07 the doc defines an explicit *escalation ladder* for how hard the
check gates completion — this ladder is new relative to the 2025-04-era advice
and is the clearest expression of the 2026 consensus [S1150]:

1. **In one prompt**: ask for the check and iteration in the same message.
2. **Across a session**: a `/goal` condition — "a separate evaluator re-checks
   it after every turn and Claude keeps working until it holds" [S1150].
3. **As a deterministic gate**: a Stop hook "runs your check as a script and
   blocks the turn from ending until it passes" (with an 8-consecutive-block
   override so a broken check can't wedge the session forever) [S1150][S1151].
4. **By a second opinion**: a verification subagent in fresh context tries to
   refute the result, "so the agent doing the work isn't the one grading it"
   [S1150].

Two corollaries with direct pewpew relevance:

- **Evidence over assertion.** "Have Claude show evidence rather than asserting
  success: the test output, the command it ran and what it returned, or a
  screenshot of the result" — because "reviewing evidence is faster than
  re-running the verification yourself, and it works for sessions you weren't
  watching" [S1150]. Cursor's cloud agents institutionalize the same idea:
  agents produce "screenshots, videos, and logs" as artifacts of the change
  working [S1166]. For pewpew this means every tier (sim, bench, fleet) should
  emit an *evidence artifact* (golden-frame diff image, captured LED trace,
  photodiode timing plot) the agent attaches to its report.
- **"If you can't verify it, don't ship it"** is listed as the fix for the
  "trust-then-verify gap" failure pattern [S1150].

The embedded world says the same thing in its own vocabulary: Espressif's
2026-06 account of agent-assisted Zephyr development (Cursor on ESP32) is built
around a Plan → Execute → Commit → Test cycle with "UART as ground truth" — the
serial console output, not the agent's claim, is what closes the loop; commits
before testing give bisectable rollback points, and a journal of failed
attempts stops the agent retrying known-dead approaches [S1169]. As of 2026-06
the vendor guidance still keeps the *human* as final evaluator on hardware
("code is cheap, judgment is not") [S1169] — full agent-closed hardware loops
are not yet vendor-documented practice (see §7).

### 2. Encoding the loop in repo config: AGENTS.md, CLAUDE.md, skills, hooks

**AGENTS.md as the cross-vendor standard — CURRENT (2026).** The repo-level
conventions file is no longer vendor-specific. AGENTS.md — "a simple, open
format for guiding coding agents … a README for agents" — originated with
OpenAI Codex, Amp, Google Jules, Cursor, and Factory (2025-08), was donated to
the Linux Foundation's Agentic AI Foundation in 2025-12, and as of mid-2026 is
used by 60,000+ open-source projects and read by 25+ agent products [S1158].
Recommended content is precisely the verify/run contract: build and test
commands, code style, testing instructions, security notes, PR conventions
[S1158]. Monorepos use nested files with a proximity rule: "the closest
AGENTS.md to the edited file wins" [S1158] — directly applicable to pewpew's
four tiers (host engine / receiver firmware / wearable / mesh node), each of
which has different build-flash-verify commands.

**Lean conventions files, with deterministic mechanisms for hard rules —
CURRENT (2026).** Anthropic's 2026 guidance on CLAUDE.md (same role, Claude
Code's native file) is notably more austere than 2025-era "stuff everything in
the memory file" advice: "CLAUDE.md is loaded every session, so only include
things that apply broadly … Keep it concise. For each line, ask: 'Would
removing this cause Claude to make mistakes?' If not, cut it. Bloated CLAUDE.md
files cause Claude to ignore your actual instructions!" [S1150]. The documented
division of labor as of 2026-07 [S1150][S1151]:

- **CLAUDE.md/AGENTS.md**: broadly-applicable commands, style, gotchas —
  *advisory* context loaded every session.
- **Skills** (`.claude/skills/*/SKILL.md`): on-demand domain knowledge and
  repeatable workflows, loaded only when relevant, including
  manually-triggered side-effectful workflows (`disable-model-invocation:
  true`) [S1150].
- **Hooks**: "Use hooks for actions that must happen every time with zero
  exceptions. … Unlike CLAUDE.md instructions which are advisory, hooks are
  deterministic and guarantee the action happens" [S1150]. PreToolUse hooks
  can return `allow`/`deny`/`ask`/`defer` decisions (or rewrite tool input);
  Stop hooks can block session completion until a check passes; TaskCompleted
  and TeammateIdle hooks gate multi-agent work [S1151][S1152]. The hooks
  reference itself warns that hook `if`-filters fail open and that hard
  allow/deny belongs in the permission system, not hook filters [S1151] — a
  layering rule pewpew's bench-safety design should copy.
- **Permission allowlists / sandbox**: the enforcement floor (see §7).

**Machine-readable project maps: AGENTS.md won; llms.txt did not.** The 2025
llms.txt hype resolved negatively for the open web: by 2026-05, 36k sites had
published one but no major LLM provider's crawler consumes it — an OtterlyAI
90-day measurement found 84 of 62,100 AI bot requests (0.1%) touched llms.txt
[S1173]. Its only real niche is documentation sites consumed by IDE agents and
docs MCP servers [S1173]. **Verdict for repo design: STALE as a repo-map
mechanism** — invest in AGENTS.md/CLAUDE.md plus self-describing commands, not
bespoke machine-readable indexes [S1158][S1173].

### 3. Everything-as-CLI with structured output; failure artifacts for machines

**CLI-first is explicit vendor guidance — CURRENT (2026).** Claude Code's
best-practices doc states flatly: "CLI tools are the most context-efficient way
to interact with external services" and recommends `gh`, `aws`, `gcloud`,
`sentry-cli` over API calls or heavier integrations; agents are also "effective
at learning CLI tools [they don't] already know" via `--help` [S1150]. The
practitioner statement of the same consensus is Poehnelt (Google, 2026-03), who
built the Google Workspace CLI agent-first: "Agents don't need GUIs. They need
deterministic, machine-readable output, self-describing schemas they can
introspect at runtime, and safety rails against their own hallucinations"
[S1168]. His concrete recommendations, as of 2026-03: `--output json` on
everything; runtime schema introspection commands (cheaper in tokens than
external docs); `--dry-run` on every mutating operation; treating agent input
as adversarial (path traversal, control characters, double-encoding); and
shipping skill files with explicit invariants rather than relying on help text
[S1168]. Claude Code itself is symmetric: `claude -p` with `--output-format
json` / `stream-json` so the agent can *be* a scriptable pipeline stage
[S1150].

**Dual-mode output.** The emerging convention is human-readable by default,
structured behind a flag, with both always available [S1168]. MCP formalized
the same duality at protocol level in the 2025-11-25 spec: tools can declare an
`outputSchema` and return `structuredContent` alongside a human-readable text
block, and "clients SHOULD validate structured results against this schema"
[S1160].

**Failure artifacts designed for machine triage.** The MCP spec encodes the
principle that failure output is agent input: tool execution errors "contain
actionable feedback that language models can use to self-correct and retry with
adjusted parameters", and clients "SHOULD provide tool execution errors to
language models to enable self-correction" [S1160]. The same design pressure
applies to test tooling: a check only closes the loop if the failure is
readable in-context — exit codes, diffable fixtures, and result files the agent
can parse [S1150]. Background agents make this structural: Copilot's coding
agent works inside an ephemeral GitHub-Actions environment "where it can
explore your code, make changes, execute automated tests and linters" — i.e.,
its entire perception of failure is CI logs and artifacts [S1165]; Cursor cloud
agents likewise verify by building/testing in the VM and surface logs,
screenshots and videos [S1166]. No 2026 source was found endorsing
human-only feedback surfaces (interactive dashboards, manual scope-squinting)
for agent loops; the interactive-only tool is treated throughout as the thing
to wrap [S1150][S1168]. Specific formats (junit-xml etc.) are assumed rather
than argued in the sources this pass — the load-bearing principle is
"pass/fail signal plus machine-parseable failure detail in the agent's
context" [S1150][S1160].

**Pewpew implication (design inference).** Every dev operation — sim run,
golden-frame diff, fleet-sim scenario, firmware build, flash, bench capture,
telemetry query — should be one allowlisted CLI verb with `--json` and a
meaningful exit code; the bench tools' failure output (logic-analyzer decode,
photodiode timing) must be text/JSON summaries, not waveform screenshots.

### 4. MCP and tool servers for instruments, serial consoles, and telemetry

**Protocol state — CURRENT but in transition (2026).** The ratified spec as of
this research date is 2025-11-25 [S1160]. A major revision finalizes
2026-07-28 (RC locked 2026-05-21): a stateless core (any request can land on
any server instance), a formal extensions framework, and — most relevant here —
**Tasks** as the official mechanism for long-running tool calls: "a server can
answer `tools/call` with a task handle, and the client drives it with
`tasks/get`, `tasks/update`, and `tasks/cancel`" [S1159]. Sampling, Roots, and
Logging enter deprecation with 12-month windows [S1159]. For pewpew, Tasks is
the protocol-blessed shape for "start a 20-minute soak capture, poll it,
cancel it" bench jobs — but it lands *after* this research date; design against
the RC, verify at final release [S1159].

**Tool-design principles — CARRIED-FORWARD (2025-09, still the reference).**
Anthropic's tool-design guidance predates 2026 but remains the baseline the
2026 material builds on: build few high-leverage tools rather than wrapping
every API endpoint; namespace related tools under consistent prefixes; return
semantic identifiers rather than raw UUIDs ("merely resolving arbitrary
alphanumeric UUIDs to more semantically meaningful and interpretable
language … significantly improves Claude's precision in retrieval tasks");
paginate/truncate for token efficiency; and iterate tool implementations
against agent evals [S1153]. Nothing found this pass supersedes it; the
2026-07 best-practices doc's CLI/MCP guidance is consistent with it [S1150].

**Tool-safety norms in the spec — CURRENT.** The spec's trust model is the
closest thing to an established read-only-vs-actuating norm: "there SHOULD
always be a human in the loop with the ability to deny tool invocations";
clients SHOULD "prompt for user confirmation on sensitive operations" and "log
tool usage for audit purposes"; and tool annotations (the read-only/destructive
behavior hints) "MUST [be considered] untrusted unless they come from trusted
servers" [S1160]. I.e., the ecosystem norm is that *the client's* permission
layer, not the server's self-description, is the enforcement point — for
pewpew's own trusted in-repo servers, annotations plus client-side allowlists
can carry the tiering (§7).

**Hardware/instrument MCP servers exist but the space is nascent — CURRENT
(2026), thin.** The best census is a curated "awesome" list started 2025-11 by
Jonathan Beri: ~20+ servers spanning serial bridges, probe-rs debug probes
(J-Link/ST-Link/DAPLink), Saleae Logic 2 analyzers, oscilloscopes,
STM32/ESP32 build-flash-monitor, Modbus/OPC UA industrial gateways, and KiCad
[S1161]. Its own scale — 47 stars, last push 2026-04 — is evidence of how early
this is [S1161]. The most-starred single-purpose servers found: an embedded
debugger MCP wrapping probe-rs (123 stars, MIT, actively pushed 2026-06)
[S1162] and a serial-port MCP server (74 stars, MIT, pushed 2026-07-07 — two
days before access) [S1163]. The conceptual case — MCP completing the embedded
"virtuous cycle" of code → observe → debug → code by giving agents bench
instruments — was argued in 2025-08 by Dorris, whose own proof-of-concept
admittedly did not fully work ("not really") [S1164]. **Finding: there is no
established, batteries-included instrument-MCP ecosystem as of 2026-07; there
are young, single-author, MIT-licensed building blocks worth reading, not
depending on** [S1161][S1162][S1163][S1164].

**Telemetry-side agents are further along.** Sentry's Seer (GA product line;
Seer Agent launched 2026-04-28) continuously scans incoming production issues,
runs background root-cause analysis over "errors, spans, logs, traces, and code
context", and can hand the fix off to "Claude Code, Cursor Cloud Agents, and
GitHub Copilot"; PR creation requires explicit human prompting and can be
disabled org-wide [S1171][S1172]. This is the template for pewpew's
fleet-telemetry tier: agents read telemetry freely, propose findings/fixes, and
never actuate the fleet from the telemetry path.

### 5. Sim-first / deterministic-first development with agents

**The principle is CURRENT; the embedded-specific evidence is thin.** The 2026
agent-workflow literature treats a fast deterministic check as the *first* rung
of the verification ladder (test suite, fixture diff — millisecond feedback)
and escalating cost/latency checks as later rungs [S1150]. Anthropic's eval
guidance (2026-01) supplies the determinism discipline: "isolate each trial
with a clean environment to prevent shared-state contamination", run multiple
trials because behavior varies between runs, and treat environment noise
(leftover files, resource exhaustion, cached data) as a first-class eval bug
[S1154]. Fixed seeds, fake clocks, and golden traces as *pewpew* mechanisms are
covered in RA-11 (golden frames — an open lane no LED project exploits) and
RA-19 (sim/emulation determinism); nothing found this pass contradicts them,
and the agent literature's demand for "a script that diffs output against a
fixture" [S1150] is exactly the golden-trace shape.

However: the strongest embedded-vendor agent workflow published in 2026
(Espressif, 2026-06) runs against **real hardware only** — no QEMU/Renode/Wokwi
appears in its loop; the bench (UART, physical device) is the ground truth at
every iteration [S1169]. So "agent iterates against sim, escalates to hardware
for confirmation" is, as of 2026-07, a *synthesis* of (a) agent-platform
verification doctrine [S1150][S1154] and (b) pre-agent simulation-first
firmware practice (RA-19), not a documented industry norm with named
practitioners. Teams that have the sim use it; the embedded-agent write-ups
that exist mostly don't have one. **This is an honest gap and a pewpew
opportunity: a pure-Python ms-scale sim (RA-11) + fleet sim + agent
verification ladder would be ahead of published practice, not behind it**
(inference from [S1150][S1154][S1169]).

### 6. Long-running, background, and multi-agent patterns

**Background cloud agents are mainstream — CURRENT (2026).** All three major
vendors converged on the same shape in 2025–2026: an agent takes a work item,
runs unattended in an isolated, repo-configured environment where it can build
and test, and emits a PR plus evidence for human review.

- **GitHub Copilot coding agent**: issue/`@copilot`-mention in, PR out; runs in
  an ephemeral GitHub-Actions environment configured by
  `copilot-setup-steps.yml`, with a firewall, default GitHub+Playwright MCP
  servers, containment via branch protections, and a hard 59-minute session
  cap [S1165].
- **Cursor cloud agents**: isolated VMs configured via
  `.cursor/environment.json` (install/start commands, snapshots, Dockerfiles —
  "environment setup is the most important step to improve the effectiveness of
  cloud agents"); they "build, test, and interact with the changed software"
  and hand back branches plus screenshots/videos/logs [S1166].
- **OpenAI Codex cloud**: parallel cloud tasks with per-repo setup scripts and
  default-restricted internet access [S1167].

The common thread for pewpew: **the repo must carry an executable description
of its own dev environment** (setup script, allowlisted commands, verify
entrypoints) because background agents have no human to ask [S1165][S1166].

**Session length is bounded by design; long-running means resumable, not
marathon.** Copilot's 59-minute cap [S1165] and Claude Code's context-window
doctrine ("the context window is the most important resource to manage";
`/clear` between tasks; subagents to keep exploration out of the main context)
[S1150] show that mid-2026 practice handles multi-hour work by *decomposition
and resumption* (named persistent sessions, checkpoints, task lists), not by
one heroic session [S1150][S1152]. A multi-hour pewpew soak test should
therefore be a *detached bench job with a queryable status/result artifact*
(cf. MCP Tasks [S1159]) that any short-lived agent session can start, poll, and
triage — not something an agent "sits on".

**Subagent fan-out and adversarial verification — CURRENT (2026).** Documented
patterns as of 2026-07 [S1150][S1152]:

- **Investigation subagents** keep file-heavy exploration out of the main
  context; results return as summaries [S1150].
- **Adversarial review**: "Before treating a task as done, have a subagent
  review the diff in a fresh context and report gaps" — fresh context matters
  because the reviewer "sees only the diff and the criteria you give it, not
  the reasoning that produced the change" [S1150]. The doc also warns about
  reviewer over-reporting: told to find gaps, a reviewer will; scope it to
  correctness-affecting findings [S1150].
- **Writer/Reviewer split sessions** and test-writer vs implementer splits
  [S1150].
- **Agent teams** (experimental, v2.1.178+): a lead plus teammates with a
  shared claimable task list, inter-agent messaging, plan-approval gates, and
  hook-enforced quality gates (TeammateIdle/TaskCompleted exit-2 to reject and
  keep a teammate working); flagship use case is debugging via 3–5 teammates
  with *competing hypotheses* instructed "to disprove each other's theories,
  like a scientific debate" [S1152]. Notably, the permission model refuses to
  let agents launder consent: "a teammate cannot approve a permission prompt or
  supply consent on your behalf", and auto mode "treats an approval claim
  relayed from another agent as untrusted input" [S1152].
- **Telemetry-watching background agents filing findings** are shipping
  product, not speculation: Seer's automatic scan → background RCA → optional
  handoff-to-coding-agent pipeline [S1171][S1172].

### 7. Safety tiers for agents driving physical hardware

**What 2026 sources actually establish** (all CURRENT):

- **Habituation data kills prompt-per-action.** Anthropic measured that users
  accept 93% of permission prompts — approval fatigue makes the mechanism
  decorative [S1155]. The 2026 replacement stack is: OS-level sandboxing
  (filesystem + proxy-enforced network allowlists; 84% fewer prompts
  internally; runtime open-sourced Apache-2.0) [S1156][S1157], plus narrow
  allowlists, plus a classifier tier for residual risk [S1155].
- **Tiered permissions with a classifier backstop.** Auto mode's published
  architecture: "Tier 1: built-in safe-tool allowlist and user settings.
  Tier 2: in-project file operations. … Only actions with real downside
  potential reach the final tier: Tier 3: transcript classifier" (Sonnet 4.6,
  two-stage, biased to block; targets irreversible destruction, security
  degradation, cross-trust-boundary ops, review bypass, credential access)
  [S1155]. Honest published error rates — 0.4% false-positive, **17%
  false-negative on overeager actions** — mean a classifier alone is not a
  safety boundary for physical actuation [S1155].
- **Structural containment at the platform.** Copilot: branch protections can
  bar the agent from touching protected branches; humans approve CI runs;
  59-minute cap bounds runaway sessions [S1165]. MCP: human-in-the-loop SHOULD,
  confirmation on sensitive ops, audit logging of tool use, annotations
  untrusted [S1160]. CLI design: `--dry-run` on every mutating verb [S1168].
  Multi-agent: consent cannot be relayed between agents [S1152].

**What the literature does NOT provide — the honest gap.** No 2026 source found
this pass gives a worked safety-tier framework for coding agents driving a
*lab bench or deployed device fleet*: nothing on canary-first actuation,
blast-radius limits for physical outputs, power-budget interlocks, or
"read telemetry freely / actuate bench with confirmation / never touch deployed
fleet unattended" tiering as such. The hardware-MCP servers are young enough
that read-vs-actuate tool separation is an implementation detail, not a
documented norm [S1161][S1162][S1163]. Adjacent 2026 material (EU-AI-Act-driven
audit-trail guidance, industrial-security frameworks) is compliance-generic
rather than dev-bench-specific and was not judged citable engineering practice.
**Pewpew must design its own bench-safety tiering**, composing the established
primitives: sandbox the session [S1157]; expose the bench only through its own
MCP/CLI tools with read-only and actuating verbs split into separately
allowlisted namespaces [S1160][S1153]; `--dry-run` everywhere [S1168];
PreToolUse-hook + permission-rule gating with the permission system (not
fail-open hook filters) as the hard layer [S1151]; hardware interlocks (bench
power switching, current limits) as the layer beneath software, on the model of
"the check that doesn't trust the agent at all"; and append-only audit logs of
every actuating call [S1160]. (Design synthesis; the composition itself is
ours.)

### 8. Eval-style regression harnesses and flake statistics

**Evals as continuously-run regression gates — CURRENT (2026).** Anthropic's
2026-01 eval guidance maps directly onto "system behaviors as scored suites":
regression evals "should have a nearly 100% pass rate" and capability evals
"can 'graduate' to become a regression suite that is run continuously to catch
any drift" [S1154]. The statistical vocabulary for nondeterminism is now
standard: **pass@k** (≥1 success in k — measures capability) vs **pass^k** (all
k succeed — measures reliability): "At k=1, they're identical. By k=10, they
tell opposite stories" [S1154]. For pewpew's noisy hardware behaviors (ESP-NOW
convergence time, frame latency under RF load), pass^k over N trials with a
threshold is the honest gate shape, and per-trial clean environments (power
cycle, fresh flash) are the eval-hygiene requirement [S1154]. Also directly
transferable: task quality bar ("a good task is one where two domain experts
would independently reach the same pass/fail verdict") and the anti-Goodhart
rule "read the transcripts … we do not take eval scores at face value until
someone digs into the details" [S1154] — an agent optimizing a scored suite
will find grader loopholes; periodic human transcript/trace review is part of
the harness.

**Flake discipline — CURRENT (2026), with 2025 practice explicitly
deprecated.** The 2026 consensus [S1170]: detect statistically (run new or
modified tests 5–10× before merge; track per-test flakiness scores);
quarantine confirmed flakes into non-blocking lanes with a ticket, an owner,
and a two-week deadline, while the merge gate runs only reliable tests; and
treat retries as diagnostic, not remedial — "a test that needs retries to pass
consistently is still broken" [S1170]. Blind auto-retry, the common 2024–2025
CI pattern, is now explicitly criticized because "retries conceal
non-determinism, making it harder to distinguish real regressions from flaky
signals" [S1170]. Note the boundary: for *hardware* tests some
nondeterminism is physics, not bug — which is exactly why the eval-style
pass^k-with-N-trials gate [S1154] rather than the binary flake/quarantine
model is the right tool for pewpew's bench suites (synthesis of
[S1154][S1170]).

### 9. What changed since 2025 — staleness audit

Patterns from the 2024–2025 agentic-coding era that mid-2026 sources treat as
superseded:

1. **Vendor-proprietary rules files → AGENTS.md.** `.cursorrules`,
   `copilot-instructions.md`-style per-vendor files gave way to one open
   standard (2025-08 launch, Linux Foundation stewardship 2025-12, 60k+ repos,
   25+ tools by mid-2026) [S1158]. **STALE: per-vendor conventions files** (as
   the primary mechanism; vendor files persist as overlays).
2. **Maximal memory files → lean files + hooks + skills.** 2025's "put every
   rule in CLAUDE.md" is now a named failure mode ("the over-specified
   CLAUDE.md"); rules that must always hold move to deterministic hooks, and
   situational knowledge moves to on-demand skills [S1150][S1151]. **STALE:
   instruction-file maximalism.**
3. **Prompt-per-action permissions → sandbox + allowlist + classifier.** The
   2025 pattern of `--dangerously-skip-permissions` inside a container, or
   clicking through every prompt, is superseded: measured 93% approval
   habituation [S1155], OS-level sandboxing with network proxying (2025-11,
   open-sourced) [S1156][S1157], and classifier-reviewed auto mode (2026-03)
   [S1155]. **STALE: both extremes (prompt-everything and skip-everything).**
4. **Wrap-everything-in-MCP → CLI-first for dev operations.** The 2025 rush to
   put an MCP server in front of every API yielded to "CLI tools are the most
   context-efficient way to interact with external services" [S1150] and
   agent-first CLI design [S1168]; MCP settles into what CLIs can't do —
   remote/stateful surfaces, instruments, hosted tool servers — and the
   protocol itself is being rebuilt around that reality (stateless core, Tasks;
   Sampling/Roots/Logging deprecated, 2026-07-28) [S1159]. **STALE: MCP as the
   default wrapper for local dev tooling.**
5. **One interactive pairing session → a portfolio of agents.** Issue-in/PR-out
   background agents in ephemeral CI environments (Copilot [S1165], Cursor
   [S1166], Codex [S1167]), investigation/verification subagent fan-out
   [S1150], adversarial fresh-context review [S1150], experimental agent teams
   with shared task lists [S1152], and telemetry-watching agents that file
   findings (Seer, 2026-04) [S1171][S1172]. **STALE: the assumption that agent
   = the chat window.**
6. **Watching the agent → reviewing its evidence.** 2026 practice reviews
   artifacts (test output, screenshots, videos, logs, diffs) after unattended
   runs rather than supervising keystrokes [S1150][S1166]. **STALE:
   synchronous supervision as the default QA mechanism.**
7. **Trusting eval scores → statistical + transcript discipline.** pass@k vs
   pass^k distinction, per-trial isolation, and mandatory transcript reading
   entered mainstream vendor guidance in 2026-01 [S1154]. **STALE: single-run
   green-checkmark evals.**
8. **Blind CI retries → statistical flake detection + owned quarantine**
   [S1170]. **STALE: retry-until-green.**
9. **llms.txt as machine-readable context → effectively dead outside docs
   sites** (0.1% of AI bot requests; no major provider support) [S1173].
   **STALE: llms.txt for repos.**

## Recommendation: what pewpew should build for its agents

Ordered synthesis (design inference from the cited findings):

1. **One verify contract per tier, encoded in AGENTS.md/CLAUDE.md.** Each tier
   (pure-Python sim → fleet sim → emulation → bench → fleet telemetry) gets an
   allowlisted CLI verb (`pewpew verify sim`, `pewpew verify bench …`) with
   `--json`, meaningful exit codes, and a failure artifact the agent can read
   in-context [S1150][S1158][S1168]. The conventions file states the ladder:
   cheapest check first, hardware only to confirm [S1150].
2. **Deterministic gates where it matters.** Stop-hook/`/goal`-style gating on
   the sim-tier checks (fast, deterministic); never hard-gate on bench checks
   (physics flakes would wedge sessions) — bench results feed the eval-style
   pass^k harness instead [S1150][S1151][S1154].
3. **Bench as an MCP/CLI tool server we write ourselves**, with read-only
   (serial monitor, logic capture read, photodiode read, telemetry query) and
   actuating (flash, power-cycle, pattern-push) verbs in separate namespaces,
   `--dry-run` on every actuating verb, audit-logged, with the permission
   system — not hook filters — as the hard allow/deny layer, and hardware
   interlocks beneath software [S1151][S1160][S1162][S1163][S1168]. Read the
   young probe-rs/serial MCP servers for shapes; do not depend on them
   [S1162][S1163].
4. **Soak tests as detached jobs, not long sessions.** Start/poll/cancel
   semantics (MCP-Tasks-shaped) with a persistent scored result artifact; any
   session — including a scheduled background agent — can triage it later
   [S1159][S1165][S1171].
5. **Fleet tier is read-only to agents, period**, on the Seer model: watch
   telemetry, file findings, propose fixes; actuation of the deployed fleet
   never happens from an unattended agent [S1171][S1172]. This tier boundary is
   ours to define — the literature won't do it for us (§7).
6. **Adversarial verification as routine**: fresh-context review subagent on
   nontrivial diffs; competing-hypothesis fan-out for gnarly mesh/RF debugging
   [S1150][S1152].

## Verdicts

- **Verification-first closed-loop workflow ("iterate until green")**:
  ascendant — the headline practice in current vendor guidance, with an
  explicit prompt→goal→hook→reviewer escalation ladder [S1150].
- **AGENTS.md (+ CLAUDE.md) conventions files**: ascendant — open standard,
  Linux Foundation stewardship, 60k+ repos, 25+ tools [S1158].
- **Hooks / deterministic gating**: ascendant — vendor-documented as the
  "must happen every time" layer distinct from advisory instructions
  [S1150][S1151].
- **Everything-as-CLI with structured output**: ascendant — explicit guidance
  from both Anthropic and Google practitioners in 2026 [S1150][S1168].
- **MCP core protocol**: ascendant but in-flux — biggest revision since launch
  lands 2026-07-28; design against the RC (stateless core, Tasks), avoid
  deprecated features (Sampling/Roots/Logging) [S1159].
- **Hardware/instrument MCP servers**: ascendant, immature — active young MIT
  building blocks, no ecosystem; read for shapes, build our own
  [S1161][S1162][S1163][S1164].
- **Background/cloud coding agents (issue-in/PR-out)**: ascendant — shipped by
  all three major vendors with the same environment-as-code + evidence-artifact
  shape [S1165][S1166][S1167].
- **Multi-agent teams with shared task lists**: ascendant-experimental —
  documented, explicitly experimental, useful patterns (competing hypotheses,
  consent non-relay) already stable [S1152].
- **Telemetry-watching agents filing findings**: ascendant — shipping product
  (Seer, 2026-04) with human-gated actuation [S1171][S1172].
- **Eval-style statistically-gated regression harnesses**: ascendant —
  vendor-documented discipline (pass^k, graduation to regression, transcript
  review) [S1154].
- **Sim-first agent iteration for embedded**: no verdict possible from
  literature — principle current, embedded practice undocumented; pewpew would
  be leading, not following [S1150][S1154][S1169].
- **llms.txt as repo/project map**: waning — measured non-consumption; AGENTS.md
  won [S1173][S1158].
- **Blind CI retries for flaky tests**: waning — explicitly deprecated in 2026
  guidance [S1170].
- **Prompt-per-action permissioning**: waning — habituation data (93% approval)
  plus sandbox/classifier replacements [S1155][S1156].
- **Human-only feedback surfaces (interactive dashboards, screenshots of
  instruments) as the agent's signal**: waning/anti-pattern — everything in the
  2026 loop is a parseable artifact [S1150][S1160][S1168].

## Code-reading queue

1. **anthropic-experimental/sandbox-runtime** [S1157] — the proxy-based network
   allowlist and filesystem profile mechanics. Answers: can a bench-driving
   pewpew session be confined so only the bench MCP/CLI verbs can reach
   hardware, with everything else sandboxed? (Apache-2.0 — reusable.)
2. **Adancurusul/embedded-debugger-mcp** [S1162] — tool inventory and naming;
   how probe-rs sessions, flash, halt/resume, and memory reads are carved into
   MCP tools; how errors are surfaced for agent self-correction. Answers: the
   concrete tool-surface shape for pewpew's S3 bench probes. (MIT.)
3. **Adancurusul/serial-mcp-server** [S1163] — read/monitor vs write tool
   split, buffering, and how continuous serial streams are windowed into
   token-bounded tool results. Answers: how pewpew should expose N node
   consoles without flooding agent context. (MIT.)
4. **awesome-mcp-hardware survey pass** [S1161] — one-hour skim of the Saleae
   Logic 2 and oscilloscope entries for capture-to-summary patterns (what does
   a logic-analyzer result look like as a tool response?). Feeds the bench
   MCP design.
5. **Claude Code hooks reference examples** [S1151] — PreToolUse JSON decision
   flow and Stop-hook gating in practice, to prototype the "sim tests must
   pass before the turn ends" gate and the "deny fleet-actuating commands"
   rule at the permission layer.

## Open questions

- **Bench-safety tiering has no literature.** Canary-first actuation,
  blast-radius limits for physical outputs, and read/confirm/never permission
  tiers for lab hardware are undocumented as of 2026-07 (§7); we design them
  ourselves from sandbox + allowlist + interlock primitives. What would settle
  it: revisit after Black Hat/DEF CON/embedded-conference season 2026-08+ for
  emerging frameworks; watch awesome-mcp-hardware [S1161] for safety-pattern
  entries.
- **MCP Tasks fitness for bench jobs.** The Tasks extension finalizes
  2026-07-28, after this research date; whether SDKs and Claude Code support it
  promptly, and whether it suits hour-long soak captures, needs re-checking
  ~2026-09 [S1159].
- **Does anyone run agent-triaged multi-hour hardware soaks unattended?** The
  bounded-session evidence (59-min caps, resumable tasks) implies detached jobs
  + later triage, but no published case study of an agent-operated HIL soak
  was found. What would settle it: forum ask (probe-rs Matrix, Zephyr Discord,
  Memfault Interrupt community) or building it and writing it up.
- **Statistical gating tooling for hardware flake vs physics-variance.** pass^k
  [S1154] and flake-quarantine [S1170] frameworks exist separately; no tool
  found that integrates trial-based statistical gates into agent-facing test
  runners for benches. Likely build-our-own atop pytest.
- **Anthropic sandboxing post publication date** recorded as 2025-11 from
  secondary coverage (InfoQ); confirm on the page and pin an archive snapshot
  when the source becomes load-bearing [S1156][NEEDS-VERIFICATION — freshness].
- **How the Claude Code best-practices doc evolves.** It carries no visible
  changelog; re-diff at next research pass to keep the STALE/CURRENT audit
  honest [S1150].
