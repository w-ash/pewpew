# Unattended checklist

Settings and checks for an unattended pewpew run: a laptop sends DDP through a private
router to stock WLED boards, and launchd keeps it running. Each line names its source. `[S###]` IDs are in
`research/SOURCES.md` (most come from
`research/verification/wled-ddp-private-router-2026-10.md`). "Backlog" means a
story of the epic "A real rig: stock WLED boards over Wi-Fi" in
`docs/backlog/v0.2.x.md`. Lines marked
(inference) have no direct source.

During setup the boards are tier 1: anything that writes to them runs
`--dry-run` first and is audit-logged. Once the run is left alone they are tier 2:
agents only read (CLAUDE.md T-7).

## 1. Before setup

- [ ] Copy the looks file, the arrangement file and its plan image to
      the laptop (the plan image path is relative to the arrangement file). A room
      file is migrated first: `uv run python -m pewpew rig migrate-room ROOM.json -o
      ROOM.arrangement.json`; `run` reads a room file for one more release, with a
      warning.
- [ ] Name each board `pewpew-N.local` as the controller `host` in the arrangement, so pewpew follows a
      board to a new DHCP address (ADR-004, 2026-11-04 amendment;
      `src/pewpew/health.py`). Backups are filed by these names
      (`src/pewpew/boards.py`).
- [ ] Back up every board into a new directory outside the repo: a backup
      is each board's `cfg.json` and `presets.json` (`src/pewpew/boards.py`),
      which hold its network settings (inference).
      `uv run python -m pewpew boards backup ~/pewpew-backups/$(date +%Y-%m-%dT%H%M) --map <rig.arrangement.json>`.
      If the backup notes "skip out-of-sequence" is on, turn it off (§3).
- [ ] Pre-flash a spare board with the same WLED version and join it to the
      private router (`.claude/skills/setting-up-wled-boards/SKILL.md`; wiring
      in `docs/breadboard-wiring.md`). WLED can reset its own config after 5
      crashes in 2 minutes [S1261]. A restore does not carry Wi-Fi
      passwords, so the spare must already be on the router
      (`src/pewpew/boards.py`). To swap it in for a board, give it that
      board's name (the skill's step 3) and restore that board's backup (§8)
      (inference: untested).
- [ ] Apply the macOS settings (§4).
- [ ] Gate the looks on the room:
      `uv run python -m pewpew verify looks <looks.json> --map <rig.arrangement.json>`.
      Every look must PASS: it checks, flashes at most 3 times a second
      (WCAG 2.3.1), is not black, and every knob changes the picture
      (`docs/authoring.md` §6, `src/pewpew/lab/verify.py`).
- [ ] Dry-run the unattended run command and check the per-board plan (backlog, DDP
      sink notes):
      `uv run python -m pewpew run <looks.json> --map <rig.arrangement.json>
      --ddp-fps <rate> --dry-run`. It also reads the looks file, so a
      refused file stops here rather than in launchd's restarts
      (`src/pewpew/run.py`).
- [ ] If the look reacts to sound, add `--audio "<exact name>"` to the dry
      run and to the LaunchAgent, with the name exactly as `uv run python
      -m pewpew audio list` prints it; never `--feature-log`
      (`docs/audio.md` §2, §6).
- [ ] Install the LaunchAgent with the same values, and again after an
      upgrade that changes its arguments. Path placeholders must be
      absolute: launchd expands no `~` (`deploy/launchd/pewpew-aura.plist`).
      `__HOST__` is the laptop's reserved address on the private router (§2);
      `__FPS__` is the DDP rate (§9), 60 by default until the test runs:

      Run it from the repo root:

      ```sh
      uv sync                                  # the template runs .venv/bin/python
      mkdir -p ~/Library/Logs/pewpew
      sed -e "s|__REPO__|$PWD|g" \
          -e "s|__MAP__|/path/to/rig.arrangement.json|g" -e "s|__LOOKS__|/path/to/looks.json|g" \
          -e "s|__HOST__|<the laptop's address on the private router>|g" \
          -e "s|__LOGS__|$HOME/Library/Logs/pewpew|g" -e "s|__FPS__|60|g" \
          deploy/launchd/pewpew-aura.plist > ~/Library/LaunchAgents/local.pewpew.aura.plist
      plutil -lint ~/Library/LaunchAgents/local.pewpew.aura.plist
      ```

## 2. Router

The example router is a GL.iNet Beryl 7 (GL-MT3600BE).
Its admin panel sets each band's mode, bandwidth and channel. Settings that
the admin panel does not show are in LuCI, under Advanced Settings
([GL.iNet user guide](https://docs.gl-inet.com/router/en/4/user_guide/gl-mt3600be)).

- [ ] 2.4 GHz band on: the ESP32-S3 has no 5 GHz [S1251]. Mode b/g/n, not
      ax or be (inference: the S3 has no ax or be).
- [ ] Fixed channel 1, 6 or 11, 20 MHz wide [S1260]. Not auto: auto channel
      selection took WLED nodes offline [S1258].
- [ ] WMM off [S158], in LuCI (inference: not yet confirmed that this
      router's driver obeys it).
- [ ] Client isolation off [S1258], in LuCI.
- [ ] Laptop wired to the router's LAN port (backlog, Wi-Fi test notes). It
      gets the internet through the router, so its own Wi-Fi need not join
      the building's network (inference).
- [ ] DHCP reservation for the laptop's wired address: the plist's `--host`
      is fixed (inference: it must not change).
- [ ] For internet, the repeater joins the building's Wi-Fi on 5 GHz only:
      Repeater options, Band Selection, 5 GHz. Main Wi-Fi on the repeating
      band "may drop for a few seconds" when the repeater reconnects
      ([GL.iNet repeater guide](https://docs.gl-inet.com/router/en/4/interface_guide/internet_repeater/)),
      and the boards are on 2.4 GHz. A wall jack into the WAN port works too.
- [ ] For a Wi-Fi sign-in page, turn on "Auto-Enable Login Mode for Public
      Hotspots" (repeater guide).

## 3. WLED, per board

- [ ] Firmware as chosen by the Wi-Fi test (§9). v16.0.0 has an open report
      of about 1 s lag that 0.15.3 lacks [S1253] (#5575).
- [ ] "Force max brightness" on, so WLED's brightness cannot scale the
      stream and pewpew's master is the only one (`src/pewpew/sinks/ddp.py`;
      [S1263]). The DDP sink notes also pin WLED brightness at 255.
- [ ] Current limiter: set for the supply. It still applies with "Force max
      brightness" on and is one setting for all outputs [S1263]. Value: not
      found (watts per bar not measured yet, backlog).
- [ ] Auto-white "Accurate" on every RGBW bar output: pewpew sends RGB and
      WLED makes W from this mode [S1250:wled00/bus_manager.cpp#L275].
- [ ] Bar outputs on the RMT outputs, with LED counts matching the arrangement
      (backlog, Wi-Fi test notes; [S1256]).
- [ ] DMX start address 1. WLED adds `DMXAddress / channelsPerLed` to the
      DDP start pixel, so 3 or more shifts the pixels (backlog, DDP sink notes).
- [ ] "Skip out-of-sequence" off (the default). pewpew restarts its DDP
      sequence at 1 on every start (`src/pewpew/sinks/ddp.py`; [S1254]).
- [ ] Realtime timeout: keep the default 2,500 ms. Not 65000, which holds the
      last frame and never falls back [S418]. (inference: it must be under the
      5 s Ethernet-pull check in §7.)
- [ ] Target refresh rate (LED Preferences, `hw.led.fps`) at or above the
      DDP rate, 60 by default. Below it WLED holds some frames and drops
      others: at 42 a board showed about 53 of 60 frames a second, and at 60
      it showed 57-60 (bench, 2026-11-09). The health row warns when it is
      lower (`src/pewpew/health.py`).
- [ ] Boot preset: a dim fallback look. The board shows it after the
      realtime timeout (backlog, WLED facts).
- [ ] UDP sync off: it is on by default, port 21324 [S257], and a board-local
      trigger fights the stream [S1258].
- [ ] Audioreactive, MQTT, Alexa and Hue off (backlog, Unattended checklist notes).
- [ ] Wi-Fi sleep off, the ESP32 default [S1250:wled00/wled.h#L372]: modem
      sleep can delay receive by a DTIM cycle [S1251].
- [ ] v16 brownout fixes: a capacitor on 3V3 (value: not found), TX power
      8.5 dBm or lower, stable USB power [S1257] (#5570).
- [ ] No settings PIN, or `boards restore` gets 401 (`src/pewpew/boards.py`).
- [ ] After the settings are final, back up again (§1).

## 4. macOS

- [ ] `sudo pmset -c sleep 0 disksleep 0 powernap 0` [S1296]; check with
      `pmset -g`.
- [ ] Lid open, on AC. pewpew holds `caffeinate -i -s`, which does not stop
      lid-closed sleep (`src/pewpew/awake.py`).
- [ ] Automatic updates off. Background Security Improvements off: they
      install silently from macOS 26.1 [S1298].
- [ ] A Do Not Disturb Focus on (backlog, Unattended checklist notes).
- [ ] Ethernet to the router, or AWDL down. With AWDL (AirDrop, Handoff,
      Universal Control) active, the Wi-Fi radio leaves the router's channel
      at a steady rhythm: pings to a board spiked to 75 ms every 0.46 s, and
      the LEDs jerked about twice a second while the preview stayed smooth
      (bench, 2026-11-09). `sudo ifconfig awdl0 down` lasts until a restart;
      AirDrop set to No One and Handoff off keep it quieter. The run logs a
      warning when AWDL is active on the Wi-Fi route to the boards
      (`src/pewpew/awdl.py`).
- [ ] FileVault blocks automatic login [S1297], and a LaunchAgent runs only
      while its user is logged in (inference). After a power loss, someone
      logs in.

## 5. Power

- [ ] Common ground across supplies, LEDs and boards [S165].
- [ ] A fuse at each supply, near it [S1261].
- [ ] 24 V supplies and boards on one switched strip (backlog). Community
      order is ground, V+, then data [S1299]; no official order found.
- [ ] If the supplies need a cap, set `--master-cap` (value: not found).

## 6. Launch

- [ ] Load the LaunchAgent in an attended session: it streams to the boards
      on every start (tier 1). `--unattended` holds the sleep assertion and arms
      the 5 s watchdog (`run --help`).
      `launchctl bootstrap gui/$UID ~/Library/LaunchAgents/local.pewpew.aura.plist`
      starts it. `launchctl kickstart -k gui/$UID/local.pewpew.aura` restarts
      it, and `launchctl bootout gui/$UID/local.pewpew.aura` stops it until
      the next bootstrap.
- [ ] The first time on this laptop, read `<logs dir>/pewpew-aura.log`
      after the bootstrap. If DDP sends fail ("No route to host") or the
      health panel shows the boards unreachable, macOS Local Network privacy
      blocks the Python binary (`.venv/bin/python`, or the interpreter it
      links to): allow it under System Settings → Privacy & Security → Local
      Network, then `launchctl kickstart -k gui/$UID/local.pewpew.aura`. The
      board-setup skill's Troubleshooting has the other fixes. (inference,
      untested: a launchd job can be blocked where Terminal is not.)
- [ ] With `--audio`, the first time on this laptop, run the attended
      microphone check (`docs/audio.md` §6): macOS may give a LaunchAgent
      only exact zeros, and the health row then says "only exact zeros".
- [ ] `--host` is the laptop's address on the private router, never another
      network: the page is unauthenticated (architecture §5, Trust model).
- [ ] Open the page from a phone on the router as `http://<router-facing IP>:7447/`.
      Use the IP, never a `.local` name: the server refuses a non-IP `Host`
      (backlog, Phone control page).
- [ ] On the phone, set Auto-Lock to Never (Settings → Display &
      Brightness → Auto-Lock). The page is served over plain http, and a
      screen wake lock needs a secure context, so the page cannot keep the
      screen on itself.

## 7. Before leaving it running

- [ ] Health chip on the page is green for every board, the render loop and
      the sleep assertion (`src/pewpew/health.py`).
- [ ] Turn on Layout on the page, blink each fixture, and check every
      output lights in the right place. Turn Layout off (backlog,
      Simulation view; `web/src/layout/LayoutTools.tsx`).
- [ ] Unplug the laptop's Ethernet for 5 s: each board falls back to its boot
      preset after the realtime timeout, and returns to the stream when
      plugged back in (backlog, Unattended checklist notes). Meanwhile the phone
      shows the red "Not connected" banner and dims its controls, which take
      no taps, then reconnects (`web/src/app/App.tsx`). (inference,
      untested: the banner comes when the phone's socket closes; until then
      the health chip reads "no frames here" once frames stop for 2 s.)
- [ ] `kill -9` the pewpew process: launchd starts it again into the current
      look, armed (`deploy/launchd/pewpew-aura.plist`). Allow up to
      10 s: `ThrottleInterval` defaults to 10 s [S1296].
- [ ] Blackout from the phone: first tap arms, and a second tap 0.4–3 s
      after the first fires; a faster one is taken as a double tap and
      does nothing (`web/src/design/useArm.ts`). One tap on RESTORE
      brings the look back (`web/src/deck/Blackout.tsx`).
- [ ] Triggers show ARMED on the page (`--armed`). Disarm takes two taps,
      timed as for blackout. Arming is one tap
      (`web/src/deck/Triggers.tsx`).

Things a restart or a trigger changes:

- An operator disarm does not survive a restart: the LaunchAgent passes
  `--armed`, so after a crash or a watchdog exit the triggers are armed
  again (`deploy/launchd/pewpew-aura.plist`).
- After a watchdog stall exit, the restart does not start a look that stalled
  (a stall marker names them): it starts the first look, the file's current
  one first and then the idle cycle's order, that the marker does not name,
  and says so on the status line, so looks that stall the loop do not take
  turns. When every look has stalled, it starts the file's current look
  again and says so. The marker is `~/.local/state/pewpew/stalled`, holds
  the names of the looks that stalled, and counts as fresh for 10
  minutes (`src/pewpew/watchdog.py`, `pewpew.run.after_stall`); the page
  shows a warning when it was used.
- The trigger log stops at 50 MB per file (`--trigger-log-max`) with one
  warning; each run starts with a header record.
- Param edits made while a trigger holds a look are dropped when the aura
  returns from the hold: the return restores the params journalled when the
  hold began (`src/pewpew/aura/looks.py`).

## 8. While it runs

Tier 2: agents read the page, the logs and `/json/info` only. A board
restore or any config write is tier 1 and runs only in an attended session
(backlog, Aura health notes), `--dry-run` first:
`uv run python -m pewpew boards restore <backup dir> --map <rig.arrangement.json> --dry-run`.

The health panel shows a problem and a fix sentence for each board, the
render loop and the sleep assertion (`src/pewpew/health.py`); the v16
brownout fixes are in §3.

## 9. Wi-Fi ingest test numbers

Take these from the new `bench/results/wifi-*` file (`bench/bench_wifi.py`,
k=3 trials of 60 s per rate) for the rig. Do not plan the DDP rate until
they exist.

- Results file.
- Router channel used.
- Firmware compared (v16.0.1 vs v0.15.4) and chosen.
- Delivered `leds.fps`, median per board at 30 and 60 fps (a DDP rate divides the loop's
  `--fps`), and pass^3
  (held = median ≥ 0.9× sent, no reboot).
- RSSI range per board.
- Chosen DDP rate (`--ddp-fps`).
