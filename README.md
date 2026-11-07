# pewpew

pewpew is a Python-first engine for addressable LEDs, for wearables,
portables and mid-scale light art (room-sized and up). Its quality bar is
better than clown mode: temporal dithering, perceptual color and smooth
motion. Looks, layered effects built from a catalog of ops, render on a host computer against a
map of where each pixel is, and Phase 1, the host engine, streams them to
stock WLED boards over DDP. A browser preview, a phone control page and an
agent interface drive the same engine, so no hardware is needed to start
([`docs/backlog/`](docs/backlog/README.md) has the plan).

## Docs

- [`docs/authoring.md`](docs/authoring.md) — how looks and ops are written and run
- [`docs/unattended-checklist.md`](docs/unattended-checklist.md) — an unattended run,
  with the LaunchAgent and board backups
- [`docs/audio.md`](docs/audio.md) — live sound from a line-in or a
  microphone, and the attended replug test
- [`.claude/skills/setting-up-wled-boards/SKILL.md`](.claude/skills/setting-up-wled-boards/SKILL.md)
  — flashing a new board and putting it on Wi-Fi
- [`docs/breadboard-wiring.md`](docs/breadboard-wiring.md) — the breadboard
  layout of a board and its level shifter
- [`docs/hardware-buying-list.md`](docs/hardware-buying-list.md) — what to buy
- [`docs/reference/catalog.md`](docs/reference/catalog.md) — every effect op,
  blend and palette
- [`docs/deployment.md`](docs/deployment.md) — deploying your own studio
  instance to Fly.io
- [`docs/backlog/`](docs/backlog/README.md) and [`CHANGELOG.md`](CHANGELOG.md)
  — what is planned and what changed
- [`bench/README.md`](bench/README.md) — the host benchmarks and soaks
- [`research/README.md`](research/README.md) — how the research is
  organized; every claim cites [`research/SOURCES.md`](research/SOURCES.md)
- [`research/synthesis/architecture.md`](research/synthesis/architecture.md)
  — the system structure, with an ADR for each decision

## Develop

```sh
uv sync                                                    # the pinned Python and dev tools
pnpm install --frozen-lockfile                             # web/'s tools: the control page and the studio
pnpm -C web exec playwright install chromium webkit        # the browsers its tests run in
uv run just check                                          # every gate CI runs
```

pnpm is the version the root `package.json` pins, and Node is in its
`engines` range.

## Play a look

Play a looks file against the real engine, with no hardware:

```sh
uv run python -m pewpew run examples/tide.look.json --preview             # in the browser
uv run python -m pewpew run examples/tide.look.json --map line:64 --ansi  # in the terminal
```

The run starts in the file's `current` look, on a 16x16 grid unless
`--map` or `--room` says otherwise. `--preview` serves
http://127.0.0.1:7447/ — positions once over websocket, then display-ready
color frames; `--ansi` renders truecolor half-blocks for ssh/CI.

## License

pewpew is licensed under Apache-2.0 ([`LICENSE`](LICENSE)).
[`research/excerpts/`](research/excerpts/) holds third-party excerpts under
their own licences ([`research/excerpts/LICENSES/`](research/excerpts/LICENSES/)).
