# RA-29: Naming the aura

Last researched: 2026-11-06
Status: reviewed. The maintainer chose the names on 2026-11-06 (Decisions).
S-ID block: S1800–S1849 (S1800–S1834 used). It also cites S022, S035,
S554, S1264, S1265, S1266, S1268 and S1512 from earlier blocks.

This study names the running engine: the package that plays looks on the
lights and takes operator requests (`src/pewpew/aura/__init__.py`;
`AuraControl` in `src/pewpew/aura/control.py`), and the run flag that
keeps it going with nobody watching. pewpew runs on wearables, in rooms
and across mesh groups (`research/synthesis/architecture.md` §1, §4), so
the name must fit all three and must not read as performance or events.
**(inference)** marks an inference; "via search" marks a fact taken from a
search summary because the page itself could not be fetched; **not found**
marks a search that found nothing.

## Key questions

1. What do comparable systems call the live, running object, and what do
   they call its saved file or state?
2. Which words are free in pewpew's own vocabulary, and which collide?
3. Which word fits a wearable, a room and a mesh group alike?

## Decisions (the maintainer, 2026-11-06)

- **The running engine is the aura** (`pewpew.aura`, `AuraControl`, the
  wire message `aura`). The maintainer chose it from the four finalists loom,
  jukebox, lantern and aura (§2), and rejected engine, run and rig as too
  generic, and the former package name because it reads as performance
  and events, while pewpew serves wearables, rooms and much else.
- **The unattended-run flag is `run --unattended`**, chosen from
  `--unattended`, `--always-on` and `--kiosk`. A run with it is "an
  unattended run": it holds a sleep assertion, arms the loop watchdog and
  leaves a failing layer out of the mix (`run --help`,
  `src/pewpew/__main__.py`).
- **The repo says nothing about when or where pewpew is used:** no
  events, places or dates of use, or schedules (CLAUDE.md, Repo habits).

The RA-27 §8 glossary carries "aura", "frame" and "unattended run".

## Findings

### 1. What comparable systems call the live object and its saved file

Most tools give the live object no name of its own: the application or
device is the live thing, and the noun goes to the saved file (project,
composition, workspace, patch, sketch). Consumer lighting names the saved
state instead (scene, effect, mode, preset, profile) (inference, from the
table).

| System | Live, running object | Saved file or state | Performance word? | Source |
|---|---|---|---|---|
| Chromatik / LX | "the Chromatik runtime"; LX's engine can run headless | project (.lxp); snapshots | no | [S1800][S035][S1265] |
| TouchDesigner | Perform Mode, "an optimized mode for live performance" | .toe, the project file | yes | [S1801] |
| Resolume | the app | composition, which "can contain a number of decks" | yes | [S1802] |
| MadMapper | the app, under "Live Performance & Control" | project; Scenes & Cues | yes | [S1803] |
| Pixelblaze | the controller and its sequencer | patterns saved to the controller; .pbb backups | no | [S1268][S1804][NEEDS-VERIFICATION] |
| xLights | the app | the show directory; sequences (.xsq) | yes | [S1805] |
| Falcon Player (FPP) | a sequence player | playlists, schedules, sequences | yes | [S022][S1806] |
| LedFx | not found | scenes and presets; `virtuals` and `scenes` in the config | no | [S1266:docs/settings/scenes.md][S1807][NEEDS-VERIFICATION] |
| WLED | the device | presets in `/presets.json`; playlists | no | [S554] |
| Ableton Live | Session View | Live Set, in a Live Project (.als) | yes | [S1512][S1808][NEEDS-VERIFICATION] |
| Max | the patcher | .maxpat; projects | no | [S1809] |
| Notch | playback inside a media server | project (.dfx); a Block is a "self-contained, single-file export" | yes | [S1810] |
| QLab | the app | workspace with cue lists and carts | yes | [S1811] |
| grandMA3 | the console | show file (patch, cues, timings) | yes | [S1812] |
| ETC Eos | the console | show file (ESF3D, ESF2, ESF) | yes | [S1813] |
| Philips Hue | an entertainment configuration that streams | scenes and effects | yes ("entertainment") | [S1814] |
| Nanoleaf | the panels | Scenes, Playlists, Schedules | no | [S1815] |
| Twinkly | the device | effects; a playlist of effects | no | [S1816] |
| Enlighted (LED garments) | the garment; "Mimic" drives several | modes | no | [S1817] |
| MIT Halo (wearable) | "a wearable lighting device" | "lighting compositions" | no | [S1818] |
| Adafruit Luminary Lanterns | the lanterns | modes | no | [S1820][NEEDS-VERIFICATION] |
| Processing | the sketch | sketch, in the Sketchbook | no | [S1821] |
| openFrameworks | the app (`ofApp`) | project, under `apps/myApps` | no | [S1822] |
| VCV Rack | the rack | patch (.vcv) | no | [S1823][NEEDS-VERIFICATION] |
| QLC+ | the Virtual Console | functions: Scene, Chaser, and a Show function for "a time driven light show" | yes | [S1824][S1264] |
| MADRIX | the app | Setup file | no | [S1825][NEEDS-VERIFICATION] |
| OpenRGB | the server | profile (.orp) | no | [S1826][NEEDS-VERIFICATION] |
| Hyperion | instance | not found | no | [S1827][NEEDS-VERIFICATION] |
| ASUS Aura | Aura / Aura Sync | effect presets; Scenario Profiles | no | [S1828][NEEDS-VERIFICATION] |
| Remote Falcon (FPP plugin) | Jukebox mode queues requested sequences | sequences | yes | [S1829][NEEDS-VERIFICATION] |

Performance and theatre words to avoid, from the table: show file and show
directory [S1812][S1813][S1805], cue, cue list, cart and workspace
[S1811][S1803], Live Set and Session [S1512], composition and deck
[S1802], Perform Mode [S1801], Block and media server [S1810], and
entertainment area [S1814].

### 2. Candidates, ranked

The collision check (2026-11-06) searched `src`, `web/src`, `docs` and
`research/synthesis` for each word used as a name.

1. **loom.** Prior use: corajr/loom, an audiovisual pattern language for
   Processing whose patterns "may unfold along a linear timeline or recur
   cyclically", archived since 2019 [S1830]; Evan Brooks' Loom, a live
   coding environment [S1831]; the Jacquard loom weaves from a sequence of
   punched cards [S1832]. For: pewpew already uses weaving words, pattern
   and a `warp` op category (`src/pewpew/fx/surprise.py:605`), and no
   collision. Against: it suggests slow handcraft rather than something
   live that takes requests (inference), and the verb means "To appear in
   an exaggerated or threatening form" [S1834].
2. **jukebox.** Prior use: Remote Falcon's Jukebox mode
   [S1829][NEEDS-VERIFICATION]. Everyday sense: a machine that plays
   recorded music, with push-buttons to make selections [S1834]. For: it
   holds saved items and plays the one anyone nearby asks for (inference).
   Against: playful, music-only, and its main prior use is a holiday
   light display; odd on a wearable (inference).
3. **lantern.** Prior use: Adafruit's CircuitPython lanterns
   [S1820][NEEDS-VERIFICATION], the same stack as the wearable tier
   (inference). For: a light word you can carry, hang or put out in
   numbers [S1834] (inference). Against: it names one light, not the thing
   that plays looks, and it brushes the example look `lorenz-lantern`
   (`docs/authoring.md:880`).
4. **aura.** Prior use: ASUS Aura Sync, RGB-lighting software
   [S1828][NEEDS-VERIFICATION]. Everyday sense: "A distinctive atmosphere
   or quality surrounding or associated with something or someone"
   [S1834], which covers a person (a wearable) and a place (a room) at once
   (inference). For: short, fits every tier, no collision. Against: it
   names the effect rather than the machine, and it carries the ASUS
   brand (inference).
5. **player.** FPP calls itself a sequence player [S022]. For: the
   everyday sense matches. Against: as generic as engine, and it can mean
   the operator (inference).
6. **lights.** The page already talks about the lights and the room (RA-27
   §8, copy rule 5). Against: `pewpew.lights` reads like a driver or sink
   package (inference).
7. **organ.** A light organ turns an audio signal into light [S1833].
   Against: it reads first as a body or church organ, and an instrument
   leans toward performance (inference).
8. **halo.** MIT's Halo is a wearable lighting device [S1818]; ColorMorph
   Halo's app has modes and saved colours [S1819][NEEDS-VERIFICATION].
   Against: a ring fits rooms and mesh groups poorly (inference).

### 3. Rejected words

| Word | Why |
|---|---|
| scene | one saved state in Hue, Nanoleaf, LedFx and QLC+ [S1814][S1815][S1266:docs/settings/scenes.md][S1824], which is pewpew's look; the mesh beacon carries a scene too (architecture §4d) |
| session | Ableton's Session View [S1512]; the mesh tier's `session_id` (architecture §4d) |
| set | Ableton's Live Set [S1512]; shadows Python's `set` |
| patch | a console's patch [S1812], which overlaps pewpew's mapping and `rebind` |
| project, workspace | generic; QLab's workspace is theatre [S1811] |
| composition | Resolume [S1802]; collides with `compose` and the compositor |
| sketch, app | the program itself in Processing and openFrameworks [S1821][S1822]; generic |
| stage, desk, console | lighting-console and theatre words; `web/src/ui/stage/` exists |
| radio, tuner | mesh radio throughout architecture §4d; "tune its knobs" is page copy (RA-27 §8) |
| glow | `Lattice.glow` (`src/pewpew/fx/field.py`) and the `glow` param (`src/pewpew/fx/expr.pyi:120`) |
| beacon, bridge, fleet, gateway | mesh-tier words (architecture §4d) |
| setup, profile, instance, mode | MADRIX, OpenRGB, Hyperion, Enlighted [S1825][S1826][S1827][S1817]; generic |
| block, entertainment area | Notch and Hue [S1810][S1814], both performance words |
| engine, run, rig | too generic (the maintainer, 2026-11-06) |

## Verdicts

Not applicable: this study weighs words, not technologies.

## Code-reading queue

None.

## Open questions

- An LED or lighting product named "loom": not found.
- The official QLab, Hue developer and Remote Falcon pages: not read (404
  or a login wall); third-party pages and search summaries stand in
  [S1811][S1814][S1829].
- Ableton's .als, MadMapper's .mad and Notch's .dfx extensions: from search
  summaries only [S1808][S1803][S1810].
- A name for the live object in LedFx, WLED or Pixelblaze: not found.
