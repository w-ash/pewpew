# Live audio: line-in, microphone and capture nodes

How pewpew hears the room's sound: through one of the laptop's inputs (an
audio interface's line-in, or a microphone), or from a capture node, an
ESP32 board at the mixer that sends its line in over the private router. The
design is ADR-009's 2026-11-06 amendments "live input" and "capture
nodes", and RA-28 (`research/topics/RA-28-audio-input.md`); the code is
`src/pewpew/audio/device.py` and `src/pewpew/audio/net.py`, and the node's
firmware is `firmware/audio-node` (§8). Lines marked (inference) have no
direct source.

Without `--audio`, a run reads the simulated features, so the lights hear
the room only when the command adds the flag.

## 1. Install

Live capture needs the `audio` extra, sounddevice 0.5.6 on PortAudio
(`pyproject.toml`). In this repo `uv sync` installs it with the dev tools,
and `uv sync --extra audio` installs it without them. The macOS wheel
brings its own PortAudio; on Linux, install `libportaudio2` first. Without
the extra, `run --audio NAME` says what to install and stops, and `audio
list` says so, lists only the capture nodes (which need no extra) and
exits 1.

## 2. Choose the input

```sh
uv run python -m pewpew audio list           # index, exact name, channels, rate, host API
uv run python -m pewpew audio list --json
```

`audio list` reads the list of inputs and opens none (tier 0). It also
lists the capture nodes that answer on this laptop's /24 (`--subnet` for
another), each with its level from its `/json/info`, never by subscribing;
§8 covers them. Name the input in `run --audio` in one of three ways
(`choose` in `src/pewpew/audio/device.py`):

- its exact name, as `audio list` prints it: the only form for an unattended run;
- its index, or a part of its name in any case, while it is plugged in;
  pewpew turns either into the exact name at launch.

pewpew refuses a blank name, `default`, which on a laptop is the built-in
microphone, a part that fits more than one input, and any name or index
of an input whose name another input has too (rename one in Audio MIDI
Setup). It never falls back to another input, so a microphone is open
only when its name is given. A spec with a `/` names a file, never an
input, so a missing file is refused rather than waited for.

`--audio-channel N` reads one channel, numbered from 0; without it pewpew
reads the mean of all the input's channels. A dry run prints what the run
would open, and opens nothing. The examples here play
`examples/warp-lane.look.json`, whose `band` and `beat` signals move its
knobs with the sound; any look with those signals reacts the same way:

```sh
uv run python -m pewpew run examples/warp-lane.look.json --map examples/canopy-60-bars.arrangement.json --audio "Scarlett 2i2 USB" --dry-run
```

An input that is not plugged in at launch is not refused: the run starts
lost and opens it once it appears, by that exact name.

## 3. While it runs

- The input opens at its own sample rate each time, with no resampling,
  including an input absent at launch. When it opens again at another
  rate, the analysis starts again at that rate, and the beat keeps its
  tempo and any tap.
- **Lost.** When a read fails or no samples come for 0.5 s, the input is
  lost: the levels fall to silence, the beat keeps its last tempo, and the
  health row says why. pewpew closes the stream, has PortAudio list the
  inputs again (PortAudio has no hotplug), and opens the input of the same
  exact name, at most once every 5 s. It lists the inputs only while no
  stream is open, because PortAudio's last `Pa_Terminate` closes every open
  stream.
- **Overflow.** When the render loop reads the input too late, PortAudio
  drops samples. The analysis restarts its hop grid and the sample clock
  its fit, and the beat free-runs for about 5 s until the fit is back.

## 4. Health

With `--audio`, the health state (`src/pewpew/health.py`) gets an `audio`
row: the input's name, its status (`opening`, `listening` or `lost`), the
beat's mode, BPM and confidence, the peak in dBFS, its overflows, a level
and one fix sentence. The page draws no audio row yet (the backlog's
"Audio on the page"), so the row is in the health message and the run's
log, and its level stays out of the page's health chip. The row warns or
fails on:

| Reason | Level | What it means |
|---|---|---|
| lost | bad | unplugged, off, or held by another program (on a Pi, PipeWire may hold the card) |
| only exact zeros for 5 s | warn | a quiet room never gives exact zeros: macOS may deny the microphone (§6) |
| held hops past 10% | warn | the input drops samples, so the beat free-runs |
| clipping | warn | the peak reached 0 dBFS: turn the gain or the mixer's send down |
| an overflow in the last minute | warn | the loop read the input too late (a node: its I2S reader did) |
| the analysis failed | bad | the last good frame stands; the run's log has the traceback |

A capture node's row also carries `node`, its numbers: address, MAC,
firmware, signal, uptime, reset reason, packets taken, samples missing,
late, stray and stale packets, reboots, epochs started by following
dropped packets, the share lost over the last 10 s, and the drift the fit
measured, which is reported and never judged. It
also warns on:

| Reason | Level | What it means |
|---|---|---|
| lost: (a refusal, or no packets) | bad | the reason names the cause: no key, another host holds the stream, the node does not answer, or an address `--allow-host` does not name |
| more than 1% of the samples lost in the last 10 s | warn | packets go missing on the Wi-Fi; past about 1% RA-28 reopens features on the node |
| signal under −70 dBm (bad under −80) | warn | move the node or the router |
| the node rebooted, in the last 10 minutes | warn | with its reset reason; `task_wdt`, `panic` or `send-stall` is a firmware fault |

The thresholds are inferences, for RA-28's bench milestone (M4) to tune.

## 5. Privacy

- Samples stay in memory: PortAudio's buffer holds a few times its 20 ms
  latency of them, and the analysis keeps one window (43 ms at 48 kHz).
  None go to disk.
- Opening an input appends an `audio-input` record to the audit log
  (`~/.local/state/pewpew/audit.jsonl`, or `$PEWPEW_AUDIT_LOG`) before the
  first stream opens, with the input, its rate (none yet for an input
  absent at launch), the feature log if any, and this privacy note. If the
  record cannot be written, the run stops and opens nothing.
- `--feature-log` is off unless asked. A microphone's 16-band log is close
  to a recording of speech: three or four band envelopes keep speech
  recognisable [S1765]. Never use it with people in the room, and never
  put it in the LaunchAgent.
- A capture node's audio crosses the private router only to its one
  subscribed host, unencrypted (the maintainer, 2026-11-06, for the line-in node), and
  lives only in RAM on both ends. Subscribing writes the same
  `audio-input` record, and a new address for the node an
  `audio-readdress` record before the first subscription to it.

## 6. An unattended run under launchd

To give an unattended run its input, add these two lines to the LaunchAgent's
`ProgramArguments`, after `--armed`, with the exact name from `audio list`
(`deploy/launchd/pewpew-aura.plist`):

```xml
    <string>--audio</string>
    <string>Scarlett 2i2 USB</string>
```

macOS may give a process without microphone permission only exact zeros
and no error [S1766][NEEDS-VERIFICATION]. Whether a LaunchAgent gets the
permission Terminal has: not found. So check it once on the pewpew laptop,
in an attended session:

- [ ] `launchctl kickstart -k gui/$UID/local.pewpew.aura`, then make a
      sound at the input.
- [ ] Read the health row (the health message on the page's socket, or the
      run's log). "only exact zeros" means macOS denied the microphone.
- [ ] If it did, allow the Python that runs pewpew (`.venv/bin/python`, or
      the interpreter it links to) under System Settings → Privacy &
      Security → Microphone, then kickstart again and recheck.
- [ ] Note the result in this section: it is the first evidence either way.

## 7. Attended replug test (tier 1)

PortAudio has no hotplug, so reopening an input is the part a fake cannot
prove. A person runs this at the bench, never an agent: opening an input is a
privacy act, and the script writes an audit record first. Results are
pass^k, never a gate (CLAUDE.md T-5).

1. Plug in the interface, start sound into its input, and find its name:
   `uv run python -m pewpew audio list`.
2. Dry run, which opens nothing:
   `uv run python -m bench.bench_audio "Scarlett 2i2 USB" --dry-run`.
3. Run it: `uv run python -m bench.bench_audio "Scarlett 2i2 USB" --trials 5
   --label mac`. It opens the input as an unattended run does and, for each
   trial, says when to unplug the cable and when to plug it back in. A trial
   passes when the input is lost within 30 s of "unplug" and listening
   again within 60 s of "plug in". The results go to
   `bench/results/audio-replug-<date>-<label>.json`.
4. Repeat once with the aura running (`run examples/warp-lane.look.json --map line:120 --audio NAME --preview`):
   unplug, wait for the health row to say lost, replug, and check the
   levels come back within about 10 s.
5. Record pass^k and anything odd (a hang, a crash, another input opened)
   in RA-28's open questions.

Untested so far: whether Core Audio's stream raises on unplug or only goes
quiet (pewpew treats either as lost), whether a replugged USB interface
keeps its exact name, and whether PortAudio writes to the run's log each
time it lists the inputs again (sounddevice hides that output by pointing
stderr at /dev/null, which would also drop pewpew's own log lines, so
pewpew does not).

## 8. A capture node (line in)

A capture node is an ESP32-S3-DevKitC-1 N8R8 with a PCM1808 converter. It
sends raw 48 kHz mono audio, 100 packets a second, to the one host that
subscribed, and does no analysis: the host analyses it as any input
(ADR-009 "capture nodes"). It joins the private router only
(`docs/unattended-checklist.md` §2). Parts: `docs/hardware-buying-list.md` §4.5.
Wiring: `docs/breadboard-wiring.md`, "Capture node". Flashing, keys and
Wi-Fi are tier 1: a person does them at the bench, never an agent.

**Build (tier 0).** `just firmware` builds the image in the pinned
ESP-IDF v6.1 Docker image, as CI's Firmware job does on each change under
`firmware/`. With ESP-IDF v6.1 installed instead:
`idf.py -C firmware/audio-node build`. The image is Apache-2.0, like pewpew; a
published `.bin` ships `firmware/audio-node/THIRD_PARTY_NOTICES.md`.

**Key and flash (tier 1, attended).** Each node has its own random
32-byte key, which signs pewpew's subscriptions: the host keeps it in
`~/.local/state/pewpew/audio-keys.json` (owner-only), the node in its
`nodekey` partition. Improv has no command to carry it [S1785], so it goes
in with the firmware.

1. Plug the board's UART port into the Mac and find the port:
   `ls /dev/cu.*` before and after (`/dev/cu.usbserial-*`).
2. Read its MAC, from the ESP-IDF environment:
   `python -m esptool --port /dev/cu.usbserial-XXXX read-mac`.
3. `uv run python -m pewpew audio key AA:BB:CC:DD:EE:FF --dry-run`, then
   the same without `--dry-run`. It audits, makes the key (or keeps the
   node's key, so a reflash needs no new one), writes the key image's CSV
   beside the key file, and prints the flash command.
4. A new board only: `idf.py -C firmware/audio-node -p /dev/cu.usbserial-XXXX
   erase-flash`, which clears WLED or the demo.
5. Flash with the key: `idf.py -C firmware/audio-node -p
   /dev/cu.usbserial-XXXX -DNODE_KEY="<the CSV path>" flash`. A later
   reflash without `-DNODE_KEY` leaves the key as it is. The build folder
   remembers `-DNODE_KEY`; before flashing another node, pass its own CSV,
   or run `idf.py -C firmware/audio-node fullclean`.
6. `idf.py -C firmware/audio-node -p /dev/cu.usbserial-XXXX monitor` shows
   the log: `pewpew-audio-node … up, reset reason poweron`.

**Wi-Fi and name (tier 1).** Move the cable to the USB port
(`/dev/cu.usbmodem*`) and run, dry first:

```sh
uv run python -m pewpew wifi /dev/cu.usbmodemXXXX --ssid "PRIVATE ROUTER" --keychain --name pewpew-line-1 --dry-run
uv run python -m pewpew wifi /dev/cu.usbmodemXXXX --ssid "PRIVATE ROUTER" --keychain --name pewpew-line-1
```

The node's HTTP is read-only, so it takes its names over Improv before it
joins (`src/pewpew/provision.py`). Role names are `pewpew-line-N`.

**Check (tier 0).** `curl -s http://pewpew-line-1.local/json/info` shows
`"brand": "pewpew"`, `"key": true`, the boot `nonce` and the `peak`.
`uv run python -m pewpew audio list` lists it under "Capture nodes", and
`boards scan` lists it as a node, never as a board. Its RGB LED is off
without a network, blue on it, and green while it streams.

**Run it.** On the bench, subscribing is tier 1, so name the node's
address with `--allow-host`; the run refuses a node without it, and one
whose name resolves to another address:

```sh
uv run python -m pewpew run examples/warp-lane.look.json --map line:120 --audio net:pewpew-line-1 --allow-host 192.168.8.42 --preview --dry-run
uv run python -m pewpew run examples/warp-lane.look.json --map line:120 --audio net:pewpew-line-1 --allow-host 192.168.8.42 --preview
```

For an unattended run, put `--audio` and `net:pewpew-line-1` in the
LaunchAgent (§6), with no `--allow-host`: an unattended run subscribes to
its node wherever DHCP put it, and audits each new address. The holder
keeps the stream: while the aura renews its subscription, no other host
can take it, and another host gets it 3 s after the aura stops. With
`--host` set to the private router's side, the socket binds there.

While it runs: no packet for 0.5 s is lost, as for a device (§3). The
supervisor renews the subscription every second, and looks the name up
and reads `/json/info` again whenever no packet came since its last pass.
A reboot starts a new epoch: the beat keeps its tempo, and its fit takes
5 s to come back. A lost packet holds about 7 hops; a packet from far in
the future is dropped as a stray; a late or repeated one is dropped. A run
subscribes only to the node it first subscribed to: if another node
answers at its address (DHCP moved them), the input is lost and says so
until the node is back there or the name leads to it again.

## 9. Attended node bench (tier 1)

A person runs these with a bench node on the private router, never a deployed
one, and never an agent. Each step is one trial: record pass^k, never a
gate (CLAUDE.md T-5). The script is `bench/bench_node.py`: a dry run
first, an audit record before the first subscription, a summary in
`bench/results/audio-node-<date>-<label>.json`, and with `--trace PATH`
the packet trace (headers and arrival ticks, no samples), which
`TraceSource` replays over a seeded signal.

```sh
uv run python -m bench.bench_node pewpew-line-1 --allow-host 192.168.8.42 --dry-run
uv run python -m bench.bench_node pewpew-line-1 --allow-host 192.168.8.42 --seconds 120 --label stream
```

| # | Step | Do | Passes when |
|---|---|---|---|
| 1 | Flash | §8, steps 1–6 | the log says `up, reset reason poweron`; `/json/info` has `"key": true` |
| 2 | Provision | §8, Wi-Fi and name | `wifi` prints the IP and `Named pewpew-line-1`; `audio list` shows the node |
| 3 | Stream | 120 s run, music into the line in | `loss` under 0.1% (ADR-003's unicast figure) and no gap over 20 ms; LED green |
| 4 | Drop Wi-Fi | in a 120 s run, turn the router's 2.4 GHz radio off for 10 s, then on | one gap about the outage long, `reboots` 0; streaming again within 10 s of the radio |
| 5 | Reboot | in a 120 s run, press RST | `reboots` 1; streaming again within 15 s |
| 6 | Forced I2S overflow | in a 60 s run, press and hold BOOT once | `overflows` 1 or more, and a gap as long as the rise in `/json/info`'s `overflow_samples` |
| 7 | 1 h soak | `--seconds 3600 --label soak --trace soak.trace` | `loss` under 1% (RA-28's revisit line), no reboot; note the drift |
| 8 | Tone | a generated 1 kHz sine on the line in alone; `--seconds 2 --label tone --tone tone.bin` | `tests/test_audio_wire.py` passes with `tone.bin` as `tests/fixtures/audio_net/tone-1khz-node.bin` |

Afterwards, put the soak trace in `tests/fixtures/audio_net/` (it holds no
audio) and record pass^k and anything odd in RA-28's open questions. The
thresholds in steps 3–5 are inferences for M4 to settle. Untested so far:
the PCM1808 module's labels and regulator, the N32R16V's octal flash, and
how often the router's channel drops a 100-packet-a-second stream.

