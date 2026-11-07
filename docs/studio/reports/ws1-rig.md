# ws1: rig core

Workstream 1 built `src/pewpew/rig/`: the pydantic models, the dims-expression evaluator, the
catalog loader with its digest, twelve catalog data files, poses, the `ring` and `array` presets,
the pure compiler, migration, the committed JSON Schemas, the golden-rings example and
`run --map file.json`. `uv run pytest` passes 311 tests (2 xfailed) in about 2 s.

**Contracts.** No contract in `docs/studio/contracts.md` turned out wrong or unbuildable. The API
matches `contracts.md:27-57`, with these additions and one narrowing:

- `FixtureInstance.attachments` has one key per anchor that accepts an attachment. For the bar
  that is `end_a` and `end_b`; for the tube, whose ends accept nothing, it is `{}`.
- `FixtureInstance` also carries `group`, `controller`, `output`, `chain`, and
  `attachment_matrices`, which gives each attachment's world frame as 16 column-major floats.
- `OutputSlice` also carries `chain`. Its `led_type` is the firmware's type number (30, 22), or
  None.
- `CompiledRig` also carries `controller_slices` (per controller `{start, count}` for DDP) and
  `feeds`. `to_json()` includes `issues`, `report`, `positions_m` and `normals`.
- The three items the coordinator added are in: `Catalog.to_json()`, the 200-fixture cap
  (`too_many_fixtures`, checked by the models before any group expands and again in
  `compile_rig`), and a `pyproject.toml` change of one line (`pydantic>=2.14`). `uv.lock` changed
  too, so expect a lock conflict with ws3; `uv lock` after the merge resolves it.

## What is where

| Module | Contents |
|---|---|
| `models.py` | `Sourced` with its subclasses, the eight catalog kinds, `Arrangement` v1, `Issue`, `RigError`, `Instance`, `WiringPlan`, `FixtureInstance`, `OutputSlice`, `ControllerSlice`, `CompiledRig`, `json_schemas()` |
| `expr.py` | `parse` (an `ast` whitelist: numbers, names, `+ - * /`, unary ±), `evaluate`, `names`, `resolve` (dependency order, names any cycle) |
| `catalog.py` | `load_catalog()` (cached per root), `read_catalog()`, `Catalog` (`get`, `dims`, `num`, `spec`, `led_type`, `digest`, `entity_digest`, `to_json`), `FixtureSpec` (`t_px_s`, `bytes_per_px`, `current_a`) |
| `pose.py` | quaternion ↔ matrix, `aim`, `compose`, `to_three`/`from_three`, `to_mvr`/`from_mvr`, `anchor_frame` |
| `presets.py` | `ring`, `array`, `describe_presets` |
| `compile.py` | `compile_rig`, `expand`, `contain` |
| `wiring.py` | the `auto_wire` stub, for ws2 to replace |
| `migrate.py` | `migrate`, `STEPS` (empty), `LATEST = 1` |
| `data/<kind>/<id>.json` | the twelve entities in the brief |
| `examples/golden-rings.json` | two rings of 24 bars, one S3, `"wiring":{"auto":{"target_fps":40}}` |

`load_arrangement` lives in `__init__.py`, as design §6 places it (`domain-model.md:278`). It
takes a dict, a path, or a string; a string that starts with `{` is read as JSON. Pydantic errors
become issues whose `code` is the pydantic error type (`extra_forbidden`, `bad_quaternion`,
`quat_and_aim`, `too_many_fixtures`, ...).

## Decisions and deviations from the design

**Data files.**

1. **Provenance strings.** The design's source keys stay as the first token of each `src`, with
   the full location after them, for example the key `RES-038` followed by the fixture notes,
   and the key `IMG-dims` followed by Clen's diffuser dimension drawing. Prototype lines are
   cited as `docs/studio/prototype/golden-tubes-3d.html:<line>`.
2. **`BL:` cites.** The design's `BL:` cites point at lines that exist only in the main
   checkout's uncommitted backlog edits; this branch's `docs/backlog/v0.2.x.md` has 195 lines.
   I re-cited them to the design's own lines. The bar's `color_order` source is now "not
   measured; the RES-034 bench test settles it" in place of "open per BL:206".
3. **Every fact carries provenance.** Literals that are facts became `Sourced`: `pixels.count`,
   `leds_per_pixel`, `channels`, the tube's `facing`, `beam_deg` and `v_nominal`. The bar's
   unnamed literals moved into `dims` as `strip_w`, `strip_t` and `led_h`, with their values
   unchanged. `Sourced.status` is required; `src` is required unless the status is `derived`.
   The design's firmware example has no `status`, so I added `"stated"`.
4. **Cable areas.** These are 1.309 mm² (16 AWG) and 0.823 mm² (18 AWG), derived from the AWG
   formula. The Wikipedia table rounds 16 AWG to 1.31 mm² but lists 13.17 mΩ/m, which only the
   unrounded area reproduces. A test checks ρ/A against 13.17 and 20.95 mΩ/m.
5. **eye-v0.** The design describes it only in words (`domain-model.md:263`), so I built it from
   the prototype's eye (`golden-tubes-3d.html:354-378`) without its 3 mm bevels: the point's plug
   plus a 30 × 20 mm blade with a 16 mm slot. It needed two schema additions, both for ws1b:
   - `Part.axis` (`"y"` by default). With `"z"`, the profile's 2D coordinates are (x, y) and
     `range_m` runs along z.
   - `profiles` on `attachment_type`.

   The CSG has no union, so the blade is two parts: a rect minus the slot, and a semicircle made
   as a circle minus a rect.
6. **Dig-Octa.** It gained `groups`, which the schema requires. It has no `lead_max_m`, because
   the design gives none.
7. **Ids.** Catalog ids are unique across all kinds, and each file's name must equal its id.

**Models.**

8. **Concrete `Sourced` classes.** `Sourced` is a base class with concrete subclasses
   (`SourcedNum`, `SourcedInt`, `SourcedText`, `SourcedVec`, `SourcedChannels`, `SourcedGender`,
   `SourcedPinmap`), because pydantic generics give unreadable `$defs` names.
9. **Ring groups.** Their parameters sit flat on the group object, as the design's JSON example
   writes them (`domain-model.md:151-154`), not under the `params` that the §1 table names.
10. **Array groups.** `counts` has one or two entries, `steps_m` has one vector per count, and
    `member` is a `Pose` (an offset plus the one member rotation). Members are numbered
    row-major.
11. **`AutoWiring` defaults.** These are the design's: `target_fps` 40, `fixtures_per_output`
    None, `max_hop_m` 3, `hop_slack` 1.2, `connector_load_fraction` 0.75,
    `max_drop_fraction` 0.10 and `psu_load_fraction` 0.8. ws2 can change them in `models.py`.
12. **Quaternion canonical form.** When w = 0, the first nonzero of x, y and z is made positive,
    so each rotation has exactly one stored form.

**Compiler.**

13. **Authoring order.** Groups come first, in list order, then free fixtures. Unwired fixtures
    follow every chain in this order.
14. **Ring length.** The ring's L is the distance from the `end_a` anchor to the `end_b` anchor,
    not a dim named `length`, so any fixture type with both end anchors can be a ring member.
15. **Attachment frame** (`pose.anchor_frame`, inference). The origin is the anchor, +y points
    along the anchor's `dir`, and +z is the host's +z, so `end_a` is Rz(180°). The test of the
    4.039 m width uses it: each tip is at local `(0, len, 0)`.
16. **MVR.** The design leaves open whether u, v, w are rows or columns
    (`mvr-spec.md#L805-L823`). I read them as the columns of the rotation, with o as the offset;
    this is an inference.
17. **Contain.** It computes `(p − lo)/s + (s − extent)/(2s)`, which equals the design's formula
    and makes the longest axis come out at exactly 0.0 and 1.0.

**Validation implemented**, all from design §6 (`domain-model.md:302-321`):

- **Errors:** unknown fields; unresolved references (types, attachments, anchors, chipsets,
  connectors, firmware, controllers, outputs, PSUs, cables, chains, profiles); duplicate ids; bad
  quaternions; both `quat_xyzw` and `aim`; `attach_mismatch`; `fixture_in_two_chains`;
  `output_used_twice`; `mixed_pixel_format`; `missing_led_type`; expression and profile cycles;
  `feed_range`; `too_many_fixtures`; `version_too_new`.
- **Violations:** `output_over_cap`, `controller_over_cap` and `mixed_led_type_group`.
- **Warnings:** `output_over_warn` (over 800 px), `controller_over_advised` (the Dig-Octa's
  2,000) and `unwired`.

**Not done.**

- The design's map-file watch and the preview's positions resend (`domain-model.md:286-288`):
  neither is in this brief.
- `--strict`.
- `fixture_rows`: each fixture's pixels are contiguous, so `pixel_start` and `pixel_count` give
  the same thing.
- The flat-chord warning: it is a test on the bar's data instead
  (`tests/test_rig_catalog.py::test_bar_dims_and_the_flat_chord_check`).
- The timing, drop, hop, lead and assumed-value warnings, and the electrical violations: these
  belong to ws2.

## Open issues

- **ws2.**
  - It replaces the body of `wiring.auto_wire`, which returns a `WiringPlan` and today leaves
    every fixture unassigned with one `unwired` warning.
  - It sets `CompiledRig.report`.
  - The golden-rings example has one S3, with four outputs, as the brief specifies. At the
    default cap, auto-wiring makes six chains of eight (`domain-model.md:365`), so it will need
    more outputs than one board has.
- **ws1b.** It needs `Part.axis`, `attachment_type.profiles` and the attachment frame above.
  `host:<profile>` refers to the host's profiles, and `compile_rig` checks that the host has
  them.
- **Measurements.** Everything in design §9 is still open (`domain-model.md:369-383`), including
  the bar's cross-section, its end caps, the pixel lattice, the colour order, the tube's speed and
  the connector rating.

## Sources

- Design and contracts: `docs/studio/domain-model.md`, `docs/studio/contracts.md:25-67`.
- Prototype: `docs/studio/prototype/golden-tubes-3d.html:263-275`, `:289-297`, `:354-378`,
  `:380-391`, `:422-442`.
- Fixture record: the maintainer's fixture notes, not public (INV-001, INV-002, RES-003,
  RES-008, RES-010 to RES-012, RES-015 to RES-018, RES-028, RES-030, RES-031, RES-033, RES-034,
  RES-036, RES-038, Q-004, Q-011, Q-012), and its vendor documents: Clen bar diffuser dimensions,
  beam angle and joining images; Clen 360 tube dimensions; SK6812RGBW datasheet p. 5
  (TH+TL = 1.25 µs ± 600 ns, Trst 80 µs, both checked); UCS1903N datasheet p. 4 (1.25 µs per bit
  in its example) and p. 5 (reset > 24 µs), both checked.
- WLED v16.0.1, all lines checked against the tag:
  - [const.h L86-L89](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L86-L89)
  - [L92-L93](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L92-L93)
  - [L324](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L324)
  - [L332](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L332)
  - [L543-L551](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L543-L551)
  - [L575](https://github.com/wled/WLED/blob/v16.0.1/wled00/const.h#L575)
  - [settings_leds.htm L494-L496](https://github.com/wled/WLED/blob/v16.0.1/wled00/data/settings_leds.htm#L494-L496)
  - [udp.cpp L477](https://github.com/wled/WLED/blob/v16.0.1/wled00/udp.cpp#L477)
- MVR spec: [mvr-spec.md L805-L823](https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/mvr-spec.md#L805-L823)
  (checked).
- QuinLED Dig-Octa: https://quinled.info/quinled-dig-octa-brainboard-32-8l-specifications/
  (ESP32-WROOM-32UE, LAN8720A, 5.12 V outputs and about 2,000 LEDs for WLED, all checked).
- Data lead length: https://quinled.info/2021/03/10/maximum-length-data-wire-leds-ws2812b-sk6812-ws2815
  (not opened; cited by the design).
- Wire gauge: https://en.wikipedia.org/wiki/American_wire_gauge (16 AWG: 1.291 mm, 1.31 mm²,
  13.17 mΩ/m; 18 AWG: 1.024 mm, 0.823 mm², 20.95 mΩ/m; checked).
- Mean Well LRS-350-24: https://www.meanwell.com/Upload/PDF/LRS-350/LRS-350-SPEC.PDF (not opened;
  14.6 A per planning report A3).
- M12 rating: https://www.automationdirect.com/pn/7000-12701-0000000 (cited through RES-033; not
  opened).
- three.js: https://threejs.org/docs/pages/Matrix4.html, https://threejs.org/docs/pages/Quaternion.html.
