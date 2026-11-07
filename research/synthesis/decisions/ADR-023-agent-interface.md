# ADR-023: Agent interface to the effects engine — a pure service, a CLI, and MCP as an optional adapter

Status: Proposed (2026-11-05)

## Context

ADR-021 and ADR-022 give the engine a large typed vocabulary: ops, blends,
signals and routes, saved as looks. An agent can compose with it only if
it can read the vocabulary, check a look before running it, see and
measure what the look renders, and change a running engine without risk.

The repo's doctrine already fixes the shape. ADR-018 sets the access
tiers: tier 0 read-only and free, tier 1 allowlisted actuation with
`--dry-run` and an audit log, tier 2 (the deployed fleet) read-only, and a
CLI first with MCP as the remote surface. `test-and-feedback.md` §2 makes
every action a CLI verb with `--json` and exit codes, and names a
screenshot-only loop as the anti-pattern. Since ADR-018 the MCP spec
2026-07-28 went final: it is stateless, keeps cross-call state in
server-minted handles, wants a deterministic `tools/list` order, and lets
a tool return structured content and an image together. The Python SDK v2
renamed its server class to `MCPServer`.

## Decision

- **`pewpew.lab` is a pure service layer.** The CLI and the MCP server are
  thin adapters over it. Its functions are `catalog`, `describe`,
  `check_look`, `explain`, `render`, `sheet`, `metrics`, `compare` and
  `vary`. Each returns a frozen dataclass with `to_json()`, so `--json`
  output and MCP `structuredContent` are the same object. Results never
  hold arrays: `render` returns `Rendered{handle, spec, metrics,
  warnings}`, where `spec` is the normalized render spec the handle
  hashes, and its frames come back separately, from the call or through
  the cache. `check_look` takes a looks book (a `.look.json` file is one,
  ADR-006 amendment "layered paths") or a single look. `vary` wraps
  `surprise.generate` and `mutate` (ADR-022) and so takes the mapping. The
  only I/O is the render cache.
- **Root results are frozen but not slotted.** A result an MCP tool
  returns at the root is a frozen dataclass without `slots`, its defaults
  given as values (`tuple[...] = ()`), never `default_factory`, and its
  type and every type it names defined at module level, never imported
  only under `TYPE_CHECKING`. Values nested inside a result may stay
  slotted (`pewpew.metrics.Metrics`, `pewpew.sheet.Sheet`). Observed in
  `mcp` 2.3.0 [S1468]: the SDK reads each root default with `getattr` on
  the class, which on a slotted class gives a slot descriptor, and then
  publishes the tool's `outputSchema` as null with no error; a
  `default_factory` field is published as required; a name it cannot
  resolve fails registration.
- **Problems have stable codes:** `unknown-op` (a node runs an op that
  does not exist), `unknown-key` (a key or a param the thing does not
  have), `wrong-kind` (a value of the wrong type or shape), `out-of-range`
  (a value past its range or options, or too many of a thing), `missing`
  (a required key, file or choice is not there), `bad-ref` (a name that
  refers to nothing, such as a knob address in a set, a route or a front
  list, or an id used twice), `cycle` (nodes that read each other),
  `wrong-dims` (an op the map's dimensions do not support),
  `wrong-version` (a looks file of another version) and `not-a-look`
  (not JSON, or not a look or a looks file, such as a layer's program
  given whole). One mistake has one code wherever it is written. Each
  problem carries a path, a reason in `ParamSet.parse` wording (ADR-022's
  codec), a did-you-mean, the valid values, a corrected example and the
  fix in words, all in its JSON. Reasons pass `errors.scrub`, so they
  name no file.
- **CLI verbs.** Each module adds its own parser, as the existing commands
  do; `__main__` dispatches every verb to its own handler.
  - Tier 0, offline: `python -m pewpew fx
    catalog|show|check|render|sheet|metrics|compare|explain|vary`, each
    taking a file or `-`, plus `verify looks FILE|DIR`, the content gate:
    the look checks, flashes at most 3 times a second, is not all black,
    and every knob is live.
  - Tier 0, live: `observe URL [--seconds S] [--sheet PATH]`
    (`pewpew.remote.observe`, built) reads the aura state, status, params
    and health and the frames the preview streams for `S` seconds of
    engine time, then reports metrics over them and, on request, a sheet.
    It never sends a control message. `pewpew.remote.client` is the wire
    client under it and under `push`.
  - Tier 1: `push URL LOOK [--fade F] [--set PATH=V] --dry-run`.
  - `run PATTERN --looks FILE [--map SPEC]` plays a version-4 looks
    book, a `.look.json` included, starting in its current look (PATTERN
    when it names none) on the map `--map` names, else PATTERN's; `run
    file.py` runs a file whose pattern is a `ProgramPattern`.
  *(Superseded 2026-11-07: `run LOOKS` plays a looks file; see ADR-025.)*
  - With `--json` every verb prints one JSON document on stdout;
    diagnostics go to stderr. Exit codes: 0 ok, 1 problems or a failed
    threshold, 2 usage, 3 unreachable or an expired handle, 4 refused. 70
    stays the watchdog's.
- **Render handles are content addresses:** `r1-` plus the first 20 hex
  digits of sha256 over the normalized look, map, seconds, fps, seed and
  an engine fingerprint. The fingerprint hashes the code that renders:
  the source of every module in the `pewpew` package, read once when
  `pewpew.lab` loads (the code the process runs), the Python and NumPy
  versions, and the bytes of any pattern file a look's `pattern` node
  runs, as loaded for that render (not the package version or a catalog
  hash; rejected below). *(Since 2026-11-07 no look runs a file, so the
  package source alone counts; see ADR-025.)* Frames are cached under `$PEWPEW_CACHE` (default
  `~/.cache/pewpew/renders`) in a size-capped LRU. The cache only saves time: a missing handle is an error that says
  to render the same spec again, which gives the same handle. `verify
  looks` renders fresh and never reads the cache, so the content gate
  never passes on a stored frame.
- **Contact sheets** let an agent see a render: `pewpew.sheet` (built).
  `contact_sheet(frames, positions, fps, *, layout="auto", tiles=8,
  width=1024, labels=True)` returns `Sheet{png, width, height, layout,
  legend}`. `layout` is `strip`, `grid` or `splat`; `auto` picks a
  space-time strip for a strip (0 or 1 axes spanned), labeled tiles for a
  panel whose points fill a lattice, and top-down dots for a volume, a
  room or a flat map that fills no lattice. `compare_sheet` draws two
  renders in rows labeled A and B, at the same times. A tile is at least
  200 px, the long edge at most 1,568 px, the width 896 to 1,568 px, and
  the default about 1024×560, about 740 image tokens. Labels use an
  embedded 5×7 bitmap font.
- **PNG without a dependency.** `pewpew.png.encode_png` writes 8-bit RGB
  with the standard library: IHDR, IDAT and IEND only (no `tIME`), filter
  0 on every row and zlib at a fixed level 6, so the same pixels give the
  same bytes under one zlib build. zlib-ng deflates them to other bytes,
  so the byte golden runs only on classic zlib.
- **Metrics come before pictures.** `pewpew.metrics.measure(frames, fps)`
  (built) returns a slotted `Metrics`: `flash_rate_max` (the counter moved
  out of `tests/test_canopy_patterns.py`), `mean_luma`, `p95_luma`,
  `black_fraction`, `clip_fraction`, `nonfinite`, `motion_energy`,
  `frozen_fraction`, `spatial_detail`, `palette_spread` (chroma-weighted,
  in OKLab) and `hue_clusters`. Every number but `nonfinite` is read from
  the frames as a sink shows them (`pewpew.sinks.sink.sanitize`), and
  `Metrics.flash_safe` checks WCAG's 3 flashes a second. Liveness needs
  extra renders, so `lab.metrics(..., liveness=True)` adds it with the
  method of `tests/test_param_liveness.py`. Color-difference and
  perceptual-error numbers are diagnostics, never gates.
- **MCP is an optional extra.** `pewpew[agent]` adds `mcp>=2,<3`; core
  runtime dependencies stay numpy, pyserial, watchfiles and websockets.
  The adapter lives in `src/pewpew/mcp_server.py`, which imports
  `MCPServer` from `mcp.server.mcpserver` (observed in 2.3.0 [S1468];
  `mcp.server.fastmcp` raises with a pointer to it). `__main__` imports the
  adapter only inside the `mcp` subcommand, so `import pewpew` and
  `pewpew.lab` never load `mcp` or pydantic, and `python -m pewpew mcp
  --tier 0|1` exits with "install pewpew[agent]" when it is missing.
  Transport is stdio, against spec 2026-07-28.
  - Tools, in a fixed `tools/list` order: `catalog_search`, `look_check`,
    `look_render` (structured `{handle, metrics, warnings}`, a PNG sheet,
    and the same JSON as text, as the spec asks of a tool that returns
    structured content [S1451]), `look_compare` (labeled A/B),
    `look_vary`, `engine_observe`, `fleet_status` (read-only), and at
    tier 1 only `engine_apply` and `engine_set`, both with `dry_run` true
    by default.
  - A tool that returns structured content and an image is annotated
    `-> Annotated[CallToolResult, <Result>]` and returns a
    `CallToolResult` whose `structured_content` is the result's
    `to_json()`: the SDK derives `outputSchema` from `<Result>` and
    validates against it. A bare `CallToolResult` return, or a tuple of a
    result and an image, gets no `outputSchema`, and `from __future__
    import annotations` does not change the schemas (all observed in
    2.3.0 [S1468]).
  - Each tool carries read-only, idempotent and destructive annotations.
    A tool whose result has a meaningful short form takes a
    `response_format` of `concise` or `detailed`: `catalog_search` (names
    and first sentences, or whole records) and `look_render` (the metrics
    alone, or the whole render spec). The others always give their whole
    result, which has no shorter form worth a choice. Example calls go
    in its input schema as JSON Schema `examples` [S1360], drawn from the
    catalog's examples: `Field(examples=...)` per argument, and root
    `examples` on the tool built by `Tool.from_function`. An MCP `Tool`
    has no `input_examples` field (none in `mcp` 2.3.0 or the 2026-07-28
    `Tool` model, observed).
  - A problem is answered with `CallToolResult(is_error=True)`: text that
    teaches the fix (code, path, did-you-mean, valid values and the
    corrected call), then the same `Problem` list as JSON text. An error
    carries no structured content: the TypeScript SDK client (1.30.0)
    checks structured content against the tool's output schema even on
    an `isError` result, and a problem list does not match it; the Python
    SDK client skips that check on an error (both observed). The
    adapter never raises for a user's problem: the SDK prefixes a
    `ToolError`'s text with "Error executing tool <name>: ", and shows any
    other exception only as that prefix, with the traceback in the
    server's log (observed).
  - The SDK drops an unknown top-level argument without a word (observed),
    so a did-you-mean for a misspelled key comes from `check_look` on the
    look's own keys, never from the SDK.
  - Resources: `pewpew://catalog`, `pewpew://catalog/{kind}/{id}`,
    `pewpew://looks/{name}`, `pewpew://docs/{topic}` and
    `pewpew://render/{handle}/sheet.png`. Prompts: `design-look` and
    `critique-pair`. No Tasks extension: a render takes seconds.
- **Tiers (ADR-018).** Every offline verb, `observe`, `engine_observe` and
  `fleet_status` are tier 0. `push`, `engine_apply` and `engine_set` are
  tier 1 under ADR-018's 2026-11-05 amendment: dry run first, an audit
  record before the first send, and only an engine whose every address is
  loopback (unless `--allow-host`) and whose hello lists `look`, which
  only `run --accept-looks` gives. No tool writes to the fleet. Live
  control uses the messages of ADR-020's amendment "capabilities": an
  `ack` or a `refused` that carries the request's `id`, and a look that
  names a pattern by file path is refused.
- **Agent docs, none hand-copied.**
  - `CLAUDE.md` stays canonical and gains about 3 lines that point at the
    `fx` verbs and the skill.
  - `.claude/skills/authoring-looks/SKILL.md` teaches the loop: search the
    catalog, write the look, check it, render it and read the metrics
    before the image, iterate, compare with the baseline, hand off to the
    critic. Its `references/` hold the metric meanings and look patterns,
    never a copy of the catalog.
  - `.claude/agents/look-critic.md` may only render, compare, check and
    read. It judges pairwise, in both orders, and returns a structured
    verdict. It is never a CI gate.
  - `docs/reference/catalog.md` is generated from the catalog, and a test
    fails when it drifts. `.claude/rules/looks.md` is path-scoped to looks
    and the compositor. `.mcp.json` names `pewpew` (tier 0) and
    `pewpew-live` (tier 1).
  - Allowlist entries for `.claude/settings.json` are proposed to the maintainer,
    not applied: they are permission changes.

## Consequences

- Adding an op changes no tool definition, schema or doc by hand; a golden
  snapshot of `tools/list` (names, order, annotations, schemas with their
  `examples`) proves it when ops are added, and asserts that every
  `outputSchema` is non-null, which catches a slotted root.
- A test asserts that `--json` output equals the result dataclass's
  `to_json()`, and another that each exit code is reached. Others assert
  that a changed byte in a package module or a pattern file gives a new
  handle, and that `verify looks` renders with the cache unread.
- Installing pewpew without the extra stays as light as today; `mcp` and
  `hypothesis` join the dev group, so the adapter is type-checked and
  tested, with an in-memory client.
- A handle outlives the server process but not the cache; the error text
  carries the recovery.
- Frames from `observe` are display-gamma and decimated, so metrics from
  them are flagged `approximate`, with the decimation stated.
- A vision verdict is evidence, as a bench result is (T-5): pass^k over
  trials, never a gate.

## Evidence

- [S1150][S1168] CLI first: structured JSON output, `--dry-run` on every
  mutation, runtime introspection, and evidence over supervision.
- [S1450] MCP 2026-07-28: stateless, server-minted handles for cross-call
  state, `tools/list` in a deterministic order, `server/discover`,
  Tasks as an extension.
- [S1451] MCP tools: text plus image content plus `structuredContent`, the
  JSON also as text, `isError` results "to enable self-correction", and
  state carried in an explicit handle.
- [S1452][S1454] SDK v2: `MCPServer` replaces `FastMCP` with the old path
  removed; tools return images through its `Image` type.
- [S1468][S1385] `mcp` 2.3.0 pulls in pydantic, starlette, uvicorn and
  more, and pydantic-core is a compiled wheel per platform — the reason it
  is an extra.
- [S1153] Anthropic's tool guidance: a `response_format` enum of concise or
  detailed, actionable errors, namespaced tools.
- [S1455] Example calls on a tool definition (the Claude API's
  `input_examples`) raised accuracy on complex parameters from 72% to
  90%; MCP carries them as JSON Schema `examples` [S1360].
- [S1456] Vision cost is ⌈w/28⌉×⌈h/28⌉ tokens, and images under 200 px are
  unreliable — the sheet's size floor and default.
- [S1462] PNG: CRC-framed chunks, zlib deflate data, `tIME` optional — all
  in the stdlib.
- [S1464] WCAG 2.3.1: no more than three flashes in any one second.
- [S1460][S1461] LLM judges show position bias in pairwise comparisons,
  mitigated by swapping order, and multimodal aesthetic judgments carry
  biases and only partly match people.
- [S1154] pass^k over trials and reading transcripts — how noisy verdicts
  are used.
- [S1457][S1458][S1459][S1467] Skill frontmatter and folders, subagent
  files with a tool list, CLAUDE.md under 200 lines with path-scoped
  rules, and on-demand loading of definitions.
- [S1155][S1156] The permission system, not prompt text, enforces what an
  agent may run.

## Rejected alternatives

- **MCP only.** ADR-018 and `test-and-feedback.md` §2 put the CLI first;
  an MCP-only surface leaves out shells, CI and scripts [S1150][S1168].
  MCP is the remote surface, built over the same service.
- **PIL (Pillow) for images.** 13.0.0 ships 82 platform wheels and no
  pure-Python wheel [S1463]: a compiled dependency for an RGB8 encoder the
  stdlib covers [S1462].
- **JSON Schema for `describe` and the catalog** [S1360]. ADR-006 rejected
  it for params, and the catalog extends those records. The MCP adapter
  derives each tool's input schema from its signature; the catalog stays
  the custom record that the page, the CLI and the docs share.
- **A screenshot-only loop.** It is the named anti-pattern [S1150][S1168],
  and a picture of a few hundred LEDs says little about flashing, clipping
  or a dead knob. Metrics come first and the sheet second, sized above the
  200 px floor [S1456].
- **Frames inside `Rendered`.** Four seconds at 30 fps on 3,840 pixels is
  1.4 million numbers, which `--json` would print and `structuredContent`
  would carry to the model; the handle and the cache give them to the
  sheet and `compare` instead.
- **Slotted root results**, the codebase's default for values. The SDK
  then publishes no `outputSchema` and says nothing (observed in 2.3.0
  [S1468]), so a client cannot validate or plan around the result.
- **A vision judge as a gate.** Judges show position and other biases
  [S1460][S1461], so a critic verdict is evidence handled like a bench
  result [S1154], never a CI gate.
- **The package version, or a catalog hash, as the engine fingerprint.**
  The version stays `0.0.1` between commits (`pyproject.toml`) and the
  catalog describes ops but holds none of their code, so an edited op,
  blend, kit helper or pattern file would keep its handle and be served
  the old frames, across sessions.
- **Session state on the server** (a render kept by connection). MCP
  2026-07-28 has no session [S1450]; a content-addressed handle survives
  restarts and a dropped cache costs only time.
- **The MCP Tasks extension now** [S1450]. A test render takes seconds;
  long captures can adopt it later without changing the service.
