# RA-27b: Control page, final proposal

Last researched: 2026-11-06
Status: **FINAL; the maintainer chose B on 2026-11-06.** The decisions are in
Decisions (2026-11-06), the first section, and §8 lists the questions.
S-ID blocks: S1500–S1549 and S1550–S1599 (shared with RA-27), and
S1600–S1649 (shared with RA-27c)

This proposal integrates the RA-27 studies, looks-ia (§6), page-ia (§7–§8),
actions (§10) and the design-led study (§9) of
[RA-27](RA-27-control-page-ux.md), with the visual foundations of
[RA-27c](RA-27c-visual-foundations.md). The design-led study leads, per the maintainer's
direction (RA-27, top). Visual tokens and colour meaning follow RA-27c §3 (§1
and §6.2 here). This proposal replaces the draft integration, and §9 says what
changed. WLED is not a model, so no recommendation here rests on it.

- **Code** is cited at 8853368 on `fx-ui-polish` unless a commit is named, and
  `fx-ui-polish` is still changing the page. Page paths are relative to
  `web/src/` and engine paths to `src/pewpew/`. Per their commit messages,
  9bd2c83 added a two-press header save, and f3f50f4 (the `fx-ui-polish` head
  when this proposal was written) groups the deck rows, asks a second press to
  recall over unsaved edits, and puts a "?" on every knob.
- **RA-27c §3.n** is a section of the foundations spec; **A#n** is a problem
  measured in RA-27c §2.4.
- **"(inference)"** marks reasoning, including every transfer from a product.

**Are the looks hard-coded?** No. They come from the `--looks` file
(`aura/book.py`), up to 64 per file (`book.py:104`).
- `keep` and `save…` add a look at the end (`book.py:200-201`).
- Keys 1–9 play the first nine in file order, so from nine looks on, a new
  save gets no key.
- The page cannot reorder looks (`aura/control.py:75-95`).

## Decisions (2026-11-06)

The maintainer decided these on 2026-11-06. Each quote is the maintainer's answer verbatim:
the option picked, or the maintainer's own words.

1. **Build B** (§4 B, decision 1): "B: frame + inspector (Recommended)".
2. **One one-press save** (decision 2): "One one-press save (Recommended)".
3. **Adopt the glossary** (decision 4; §3 and RA-27 §8): "Adopt the glossary
   (Recommended)", with item 5's word for motion.
4. **Martian Grotesk and Martian Mono,** not decision 7's system sans: "Let's
   go with Martian and Martian Mono - spin up a subagent to figure out how to
   thoughtfully tune it for our needs." The tuning study set each face's
   roles (RA-27c §3.1), and phase 1a built them.
5. **"Modulators" replaces "motion"** for signals. Of the heading "what moves
   the knobs", the maintainer asked: why not "Modulators". Then: "use it." The heading
   reads Modulators (lower case on the page, §6.3 rule 2), one of them is "a
   modulator", and a modulated knob's line reads
   `modulated by <name> ±<depth>`. RA-27 §12 holds the terms study behind it:
   the ? note, the seven kinds (LFO, random, beat, envelope, audio follower,
   macro, smooth), and when the sign is + or − instead of ±. The knob line
   drops ◆ (RA-27 §12.3).
6. **Defaults taken** (not asked): undo instead of two presses, in phase 2
   (decision 3); keys follow file order (decision 5); the look name leaves the
   top bar (decision 6).
7. **Blackout joins the frame row on phones** (RA-27c open question 1): the maintainer
   picked the frame row on 2026-11-06, as §4 B's phone wireframe draws it.
   The editor gets 295 px instead of 239. This reverses the own-row layout
   built in 6c1f7b9, which the phase 1a and 1b briefs recorded without the maintainer's
   words; phase 2 moves it.

The sections below use these words. The ? note's "the music" waits on a live
audio source (RA-27 open question 10).

## 1. Visual foundations

Summarized from RA-27c §3, which applies RA-27c §1; the tokens are in RA-27c
§3.8.

- **Type.** Martian Grotesk for every word, Martian Mono for keycaps and
  board addresses, and Mono's digits and signs ("Martian Figures") for
  numbers that change while shown (Decisions, item 4; RA-27c §3.1; ADR-020,
  2026-11-06 amendment). RA-27c §3.1 holds each role's size per pointer,
  tuned a step smaller after phase 1b (RA-27 §11.2). Weight 400 unless named:
  - display, 600: the playing look's name, once per page;
  - title, 600: the inspector path, sheet titles;
  - heading, 600: block heads, step names; never smaller or fainter than
    what it heads (A#3);
  - body: labels on buttons, tiles, menus and layers; tabular values;
  - label: body in text-2, for knob names;
  - eyebrow, 600 caps: badges. Caption, text-2: units, hints, keys.
- **Spacing.** Steps of 4, 8, 12, 16 and 24 px, set by the parent's `gap`.
  Groups sit at least 2× their largest inner gap apart: 4 inside a knob, 12
  between knobs and deck rows, 24 between groups; closed disclosure rows stack
  flush. A boundary gets space, else a surface, else a line (library rows
  only). Each region has one text edge and one control edge. Controls are
  28 px tall, 44 on touch.
- **Surfaces,** lighter as they rise, with no shadows: page `#0b0b0e`, region
  `#17171a` (deck and inspector cards), raised `#212124` (tiles, badges),
  overlay `#2b2b2e` (menus, find, toasts). No card inside a card; selected adds
  text-1 at 12%.
- **Colour.** Amber: the primary (solid), the playing tile, held and armed
  cues. Red: darkens, removes or failed; filled only while confirming. Green:
  connected. All else is neutral. Each sign carries a word.
- **Hierarchy.** Canvas, look name, `save` (the only solid amber, shown only
  while it can act), tiles, inspector path and values, blackout, status
  chrome. Per region: at most 3 sizes, 1 solid amber, 1 big element.
- **Signifiers.** Actions have a fill, a 1 px `--border-strong` edge or a
  text-1 word, never text-2 (static). Tiles are raised and rows flat; selected
  is the fill and 600, never amber; disabled is `--text-disabled` plus a
  reason; focus is a 2 px text-1 outline.

## 2. Design principles

1. One accent and one primary per region, shown only while it can act
   [S1561][S1550][S1577][S1579].
2. Things are tiles and actions are buttons, never the same component
   [S1568][S1578][S1587].
3. A made look is a labelled draft until saved [S1555][S1557][S1593].
4. The frame stays fixed, and the selection sets what the slot shows
   [S1563][S1527].
5. Every level has the same header slots [S1562]; an open layer's header holds
   the path (inference).
6. Undo instead of asking [S1585][S1526]; confirm only what the room sees first
   (inference).
7. One word per thing, labels always on, inline help before any tooltip
   [S1564][S1573][S1590].
8. Respond on press within 50 ms; show busy at once when the engine is slower
   [S1592].

## 3. Mental model and UI words

```
frame       now line · looks · make · cues · brightness · fade · blackout
└ look      what the lights are doing, saved under a name
  ├ main knobs  a few step knobs, each naming its owner
  ├ modulators  keep knobs moving; each lists what it moves
  └ layers      the top layer draws over the ones below
    └ layer     on · opacity · blend · order · a pattern, or steps
      └ step    draws, bends or colours
        └ knob  value · ↺ back to saved · modulated by ‘name’ ±depth
```

- **The frame is never a heading,** like Linear's inverted-L chrome
  [S1563].
- **Controls sit at the level they change.** A copy elsewhere names its owner,
  and main knobs also stay in their step [S1574]. The now line is the one
  exception (§4 B).
- **A modulator shows both ends** (inference): a modulated knob shows
  `modulated by ‘breath’ ±0.2` in text-2 (§6.2), and the modulator's row shows
  its kind and `→ freq · base`. Routes get no noun on the page (RA-27 §12.3).

**UI words** (code term), a note of ≤12 words, and where the note shows:
- **looks** (first nine): The first nine looks, on keys 1–9; find reorders
  them. Sheet.
- **layer**, shown as `pattern` or `5 steps`: One picture; higher layers draw
  over lower ones. `?`
- **step** (node): One stage of a layer: it draws, bends or colours. Sheet.
- **main knobs** (front), no caption: The few knobs this look is played with.
  Sheet.
- **modulators** (signal): A modulator keeps a knob moving: a wave, the beat,
  the music. `?` Each kind gets a help-sheet line (RA-27 §12.2).
- **brightness, max** (master, cap): Highest brightness allowed in this run. `?` on
  max.
- **shuffle** (idle cycle) [S1556]: When nobody touches anything, ↻ looks play
  at random. `?`
- **cues on/off** (trigger, arm): A cue plays a look briefly, then comes back.
  `?`

**Verbs:** surprise me, vary this, save, undo, revert, find ("like this" reads
as a Like button). Before the engine strings change, test main knobs,
brightness, step and palette in place with about five people [S1553]. Find maps
synonyms such as preset and scene [S1591].

## 4. Options

Key: `[[x]]` primary · `[x]` secondary · `x` tertiary · `(x)` tile · `((x●))`
live tile · `▒x` selected fill, 600 · `[!x]` danger · `¹` key (keyboard or
fine pointer only).

`firefly-ink` is real (layer `ink`; steps flies, bleed, tint). `tide` is
illustrative: layers sparks, echo, base, wash; base runs noise → kaleid → osc
→ fb → tint; modulators breath (LFO) and bass (audio follower).

### A. One nested page (the draft, upgraded)

The first nine looks, then `all 12 ›` to a panel with `arrange`. Save is
primary in the look header [S1562], with the §4 B states. Layers nest in place
in one scroll; the open one takes the selected fill, and its knobs are
indented (RA-27c §3.2). Lossy actions take two presses.

```
PHONE · 4 layers · base open · deck as B's, no now line
tide · changed            [[save]]▾ ⋯   display + caption; scrolls away
main knobs, modulators, layers ?, sparks, echo: as in B
▒base · 5 steps    100%  (on)     ⌄    sticky: tide › base
 noise                            ›    step names: heading; closed rows stack
 kaleid                           ›
 osc                              ⌄
   freq ━━●┆━ 1.20               ↺    knobs indent 12
   modulated by ‘breath’ ±0.2 Hz      text-2, under its knob
 fb, tint: closed rows   [▲] [▼]  ⋯    24 above, after the open group
 wash · pattern    100%  (on)
[+ layer]
```

- **Gives:** the least new code, no selection model, a layout that shows
  containment.
- **Takes:** on a phone, save scrolls away and an open layer pushes the main
  knobs off screen; 16 closed rows run about 700 px (inference); confirms get
  skimmed [S1526].
- **Scope:** §6, plus `LayerCard`, `StepList` and `LooksPanel`; engine `move`
  and `rename`.

### B. Fixed frame, layer list and inspector (recommended)

- **Frame.** The frame's controls never move; only the slot changes [S1563]. The now
  line heads the deck: the look's name ranks next after the canvas (RA-27c
  §3.5).
- **Now line.** It is the look's header (name, badge, `undo`, `[[save]]▾`, look
  menu `⋯`). It is the one control outside its level, because save must not
  move (inference). Smart Shuffle [S1555] and Superhuman's drafts [S1593] also
  keep unsaved picks apart.
- **Looks.** The first nine in file order, on keys 1–9: no pins and no file
  change. Dragging in find, as Linear reorders its sidebar [S1569], or
  `move to key…` puts a look in the first nine; the ninth becomes tenth and
  loses its key. `⌕` opens **find** [S1565][S1591][S1583].
- **Make.** Secondary buttons on their own row [S1558][S1578], 12 below the
  tiles, whose raised fill sets them apart (RA-27c §3.2).
- **Save.** One press, by state [S1559]. `▾` holds save and save as new…, as
  Geist's split menu repeats the label first, holds close variants and blocks
  destructive items [S1580].
- **Look menu.** One `⋯`, on the now line, on find rows and on a long-pressed
  tile [S1582]: rename… · move to key… · ↻ in shuffle · revert (the playing
  look, while changed) · delete, last after a divider [S1581].
- **Nesting.** With nothing picked, the slot shows the look. A picked layer gets
  an inspector [S1527][S1563] headed `‹ tide / base ▾ ⋯`: `‹` goes back,
  `base ▾` picks a sibling, and `⋯` holds replace… and remove. These change
  only the selection; the look crumb never switches looks (inference). How
  Geist's breadcrumb menu behaves was not found [S1584]. A phone's inspector
  replaces the list, as Superhuman hides the inbox while you read [S1594].
  Desktop stacks the main knobs, modulators and the list above it, with no `‹`
  (RA-27c §3.2).
- **Actions.** Act, then offer `undo` [S1585][S1526]; only blackout keeps two
  presses (inference: the room sees it first). `undo` stays on the now line
  until the engine's undo slot empties, so phones need no `z`. Toasts ("tide
  deleted") show atop the slot, never over the frame.

**Save states** (phase 1: in the look header, without `▾` or `undo`):

| State | Now line | A press sends |
|---|---|---|
| saved, unchanged | `tide ⋯` (no primary) | — |
| saved, changed | `tide · changed [[save]]▾ ⋯` | `save {name: "tide", fade: null, master: null}` |
| made look | `surprise 7 ✦ DRAFT [[save]]▾ ⋯` | `keep` → "surprise 7" |
| no current look or draft (a pattern pick) | `kept ✦ DRAFT [[save]]▾ ⋯` | `keep` → "kept", "kept 2"… (`aura/looks.py:60`) |
| a cue holds a look | `dusk · kick cue ⋯`, no save | — (`keep` refused while held); `k` shows why |
| 64 looks, a draft | save in `--text-disabled` | shows "there are already 64 looks; delete one first" (`aura/looks.py:298`) |
| no looks file | name only; no save, no looks row | — ; `k` shows `NO_LOOKS_FILE` |
| after a lossy act | `undo` before save | `undo` |

The name is display, `· changed` a caption and `✦ DRAFT` an eyebrow. At 358 px
the name truncates first (about 10 characters fit at display size,
inference); the badge, `undo`, save and `⋯` keep their width.

```
PHONE · 4 layers · 12 looks · cues in the file
nothing picked                     │ base picked
decay ━━●── 0.60 · base            │ ‹ tide / base ▾                ⋯
sides ━●── 6 · base                │ opacity ━━━● 100%  blend normal ▾
modulators ?                       │ noise                          ›
breath LFO → freq · base        ›  │ kaleid                         ›
bass audio follower             ›  │ osc                            ⌄
  → opacity · sparks               │   freq ━━●┆━ 1.20              ↺
layers ?                           │   modulated by ‘breath’ ±0.2 Hz
sparks · pattern   60%  (on)    ›  │ fb                             ›
echo · 2 steps     80%  (on)    ›  │ tint                           ›
base · 5 steps    100%  (on)    ›  │ [▲] [▼]
wash · pattern    100%  (on)    ›  │
[+ layer]                          │
modulators, layers: heading, 24 above · ‹ tide / base: title · labels text-2
═ deck, under both: a region card, rows 12 apart, 244 px ══════════
tide · changed          [[save]]▾  ⋯     display + caption; only solid amber
(dusk)((tide●))(ember)(prism)(warp)… ⌕   raised tiles 8 apart, scroll; ⌕ stays
[⚄ surprise me]  [≈ vary this]           secondary
cues on ?  (kick) (drop)                 only if the file has cues: +56 px
☀ ━━━●── 60%   fade ▾       [!blackout]  red text, grey edge; fixed last
1 layer: no layers list; `ink · 3 steps` heads its steps, then [+ layer].

DESKTOP · side column 352–512 px · base picked
deck card       tide · changed                 [[save]]▾  ⋯
                (dusk¹)((tide²●))(ember³)…(dune⁹)          ⌕
                make, then cues, then
                brightness ━━━●── − 60% +   fade ▾  [!blackout]
inspector card  main knobs, modulators ?, layers ? (▒base): as the phone
8 below         24, then tide / base ▾ ⋯ (title, no ‹) and its steps

FIND · phase 3 · a phone sheet, or ⌘K and / on desktop
⌕ find looks and actions…                      ✕
recent       (tide) (moss) (dune)
first nine   ⠿ dusk  1  ⋯   ⠿ tide  2  ⋯   …
more looks   ⠿ amber-rain  ⋯        drag above the line for a key
actions      surprise me s · vary this m · save k · blackout b b
```

- **Gives:** save and the play controls never move; the inspector scales to 16
  layers; find covers 64 looks and teaches keys [S1591][S1566]; undo ends
  almost all arming.
- **Takes:**
  - a selection model, engine work and the most new components;
  - on a phone, a picked layer hides its siblings and the main knobs, one `‹`
    away. The cost is owned, since editing a layer is not live play
    (inference);
  - the phone deck takes 244 of 844 px (RA-27c §3.2), so cues show only when
    the file has triggers, and the nine tiles scroll (about 3.6 screen widths,
    inference from the audit).
- **Scope:** §6, plus `NowLine`, `PathHeader`, `Inspector`, `Find`, `Toast`
  and `StepList` (Ark 5.40.0 ships Menu, Combobox and Toast). Engine: `move`,
  `rename` and `undo`, with one undo slot. A lossy act (delete, revert, remove,
  replace, a save over a look, a recall or make over unsaved edits) fills the
  slot with what it replaced: the book (order and `current`),
  `_deck.snapshot()`, `_made` and `_recalled`. Any other book write, a recall
  that loses nothing, or an idle-cycle step empties it, so undo never restores
  stale state. No file change; an ADR-020 amendment, and an ADR for this
  layout.

### C. Play and edit

A **play face** (main knobs and modulator meters) sits by B's frame, with
`edit ›` to B's list and inspector, as Superhuman [S1594] and Figma's Minimize
UI [S1576] hide detail. It is the smallest live surface, but it is a mode to
learn, and a look's children show only in edit, the opposite of the maintainer's ask.
It is three levels deep, past NN/g's two [S1524].

## 5. Recommendation: B

- **The design-led evidence converges on it:** a fixed frame [S1563], an
  inspector that follows the selection [S1527][S1563], one header slot per
  level [S1562], undo [S1585] and one find [S1565][S1591].
- **Page-ia's objection** (the main knobs leave the screen) is met on desktop,
  where they stay above the picked layer, as Figma's panel shows file-level
  controls with nothing selected [S1527] (inference). On a phone, B owns the
  cost.
- **Phase 1 does not depend on the choice.** Not C, because C hides the
  nesting the maintainer asked to make clear.

## 6. Shared foundations

### 6.1 Buttons

All buttons live in `ui/common/`. Ark has no Button [S1536]. Park UI [S1537],
Geist [S1579] and Figma's SDS [S1577:src/ui/primitives/Button/Button.tsx] each
use one Button with a variant prop. `Button` takes `variant`, `tone="danger"`,
`busy`, `reason` (a press says why it is off), `icon`, `shortcut` and
`confirm` (blackout only).

| Component · variant | Looks (RA-27c §3.6) | Used for |
|---|---|---|
| Button primary | solid amber, `--on-accent` 600 | save; scan and blink in their panels |
| Button secondary | 1 px `--border-strong` edge, SVG icon; a held cue: amber tint and edge | surprise me, vary this, + layer, cues |
| Button tertiary | text-1, no edge, fixed slot | undo, all N ›, defaults, add colour |
| Button secondary danger | `--danger-fg` text, `--border-strong` edge; `--danger-fill` while confirming | blackout |
| Menu (Ark) | overlay; chosen: ✓, no fill; danger items red, last, after a divider [S1581] | save ▾, look menu, layer ⋯ |
| IconButton | square, `aria-label` | ⋯ ⌕ ✕ ‹ ↺ ▲ ▼ − + |
| Toggle (Ark) | secondary; on: selected fill, 600; armed `cues on`: amber tint and edge | cues on, layout, single-key shortcuts |
| Switch | on: `--text-2` track; off: `--border-strong` edge, no fill | layer on, on/off knobs, ↻ in shuffle |
| Tile | raised, no edge; live: amber tint, ● and 600 | saved looks, catalog patterns |
| Row | flat, hover 4%; picked: selected fill, 600 | layers list, find results |
| Segment (Ark ToggleGroup) | chosen: selected fill, 600 | pattern picks, choice knobs |
| Badge | eyebrow on raised, a sign and a word, never pressable [S1586] | ✦ DRAFT, the top bar's shuffle |
| Disclosure | › ⌄, `aria-expanded` | layer row, step, modulator, ?, knob label |
| Toast | overlay, polite `aria-live`, top of the slot, ~5 s [S1585] | confirmations, one-time hints |

Rules:
1. **One primary per region** (frame, slot panel, form), never destructive, and
   none at rest (inference).
2. **Rank shows in style, not size** [S1521]. Targets follow §1; 24 px is
   WCAG's floor [S1374]. Blackout too: normal width, found by its fixed last
   place (inference).
3. **Disable only when impossible,** and say why inline
   [S1579][S1588][S1534].
4. **A menu is never the only way in** [S1582]; long-press opens the look menu
   too. Values show inline [S1573].

Retired: `TwoTapButton`, `AboutButton`, `.quiet`, `.primary`, `.look`,
`.step`.

### 6.2 Reconciled with the visual foundations

Where the draft's shared foundations differed from RA-27c §3, RA-27c wins (was
→ now):
- **Picked layer:** amber tint and edge, raised card, `▌` → selected fill, 600
  (`ui/theme.css:1374`).
- **Live tile:** amber tint and edge → tint, ● and 600; the amber edge marks
  held and armed cues.
- **Segments, toggles:** amber, or a 2 px `--text` edge → selected fill, 600.
- **Changed:** a `● changed` badge and an amber dot → `· changed` by save, and
  ↺ on knobs. ● means live.
- **Blackout:** red outline → red text, grey edge; confirming reads "again to
  black out" ("armed" names a trigger state).
- **Focus:** amber, and an amber dragged thumb (`ui/theme.css:615-619`) →
  text-1 outline.
- **Unavailable, off:** 40% opacity → `--text-disabled` and a reason; the word
  "off".
- **Modulator colours:** `--sig-1…4` go, and so does ◆; the `modulated by`
  line is text-2 and names its modulator (inference: the spec lists three
  hues).
- **Tokens:** `--surface-2` → `--surface-raised` #212124; `--edge-2` →
  `--border-strong` #7b7b7e; `--surface-1` → `--surface-region` #17171a;
  `--rail` goes, as knobs nest by indent (`StepRail` → `StepList`). The
  contrast figures are RA-27c's.
- **Type:** the bold 1.15em name → display; layer names body; step names
  heading.
- **Spacing:** a 2× row gap above make → 12; targets 24 → 28 px.
- **Knob label taps:** text-2 means static, so the underline is
  `--border-strong` (inference).
- **Layout:** the now line heads the desktop deck too; desktop stacks the list
  above the picked layer; the phone deck drops "looks ?" (RA-27c §3.2, §3.5).
- **Top bar:** no look name (decision 6).

### 6.3 Copy rules and signs

1. Buttons are verbs, and things are nouns [S1590]. "…" opens something.
2. Labels are lower case and 1–2 words; notes are 12 words or fewer. A reason
   names the fix: "vary this needs a look playing".
3. Toasts read "{noun} {past participle}" [S1585]: "tide deleted". Never say
   render, node or param.
4. These are all the signs, each shown with its word; the help sheet holds the
   notes:
   - **● on a tile:** Playing now.
   - **· changed:** Changed since saved; save updates it.
   - **✦ draft:** Not saved yet; save keeps it.
   - **↺ back to saved** (its label): Puts this knob back to its saved value.
   - **↻ in shuffle:** Takes turns at random while shuffle is on (RA-27 §13).
   - **±, +, −** in `modulated by ‘name’ ±depth`: How far a modulator moves
     this knob; saving keeps your setting. **→** in a modulator row: what it
     moves.
   - **↩ returns here:** After a cue, the lights come back here.
   - **¹–⁹:** the key itself; keyboard or fine pointer only.
   - **?** opens one line about the word before it.
   - Controls with an `aria-label` and no note: ‹ › ⌄ ▾ ⋯ ✕ ▲ ▼ − + ⠿ ⌕, and
     the ⚄ ≈ ☀ icons beside their words.

### 6.4 Learn more: one pattern

Help comes in tiers, **label, then ? note, then help sheet**, inline and never a
tooltip [S1590][S1588].
- **? note.** A quiet `?` follows each concept word that fails the party test:
  modulators, layers, blend, cues and max. A tap opens one line in the page
  flow, as an APG disclosure [S1530], the same on touch [S1532]. One is open
  at a time.
- **Knobs** get no `?`: the label is the tap target, with a dotted underline
  (the fallback in RA-27's open question 3). This replaces the head's "?" on
  every knob.
- **Badges and main knobs** get no `?`: badges are never pressable [S1586], and
  main knobs have no caption. ✦ draft and · changed get a one-time hint when
  first shown [S1595]; all three are in the help sheet.
- **Help sheet.** The top bar's `?` opens it on every device (phones have no
  `?` key), and so does the `?` key: glossary, signs and keys [S1552][S1567],
  extending `ShortcutHelp`.
- **Teach in the moment, not with a tour** [S1595]. Inside the first nine, the
  first save toasts "surprise 7 saved · key 6". Past nine, once: "surprise 7
  saved · move to key… gives it a key". Menus and find show keys [S1566].
- **Gone:** the focus-only knob overlay (`ui/theme.css:927-943`), `title`-only
  reasons and hover text [S1572][S1524].
- **WCAG 2.2 kept:** 1.3.1, 1.4.1, 1.4.3, 1.4.11, 1.4.13, 2.1.4, 2.4.7, 2.5.8,
  3.2.4, 3.3.2, 4.1.2 and 4.1.3 [S1531][S1374]. Not done: an audit, AAA,
  narrated readouts, localisation or a light theme.

### 6.5 Keyboard and empty states

- **Kept,** since moved controls break muscle memory [S1572]: 1–9, s, m, b
  (twice), l, [ ], ? and Esc (`app/App.tsx:57-59`,
  `ui/deck/Variety.tsx:31-36`). `k` moves from keep to save, and ⌘S joins it.
- **Added:** ⌘K or `/` opens find [S1565][S1583]; a phone gets ⌕, since a
  gesture alone can't be found [S1591]. `z` undoes; a phone uses the now
  line's `undo`.
- **Empty states,** one line and one path each [S1589][S1595]: "No looks yet.
  Surprise me, then save one you like." In find: "No look called 'x'", with the
  actions still listed.

## 7. Phases

One branch per phase on `fx-ui-polish`, each passing `just ready`. Phase 1
needs 9bd2c83 or later: at 8853368, `save {master: null}` drops the stored
brightness (the code reads `if master`); from 9bd2c83, null keeps the old
choice (`aura/looks.py:259, 271`).

**Phase 1: the maintainer's three complaints, on the foundations.** Page only, the same
under A or B.
1. **Tokens where phase 1 works** (deck, look header, headings, layers list):
   RA-27c §3.8's type roles, space steps, surfaces and colour roles, in px
   while the 13 px desktop root stays, since moving it resizes every rem length
   (inference). Martian goes in at the root (Decisions, item 4).
2. `Button`, `IconButton`, `Tile` and `Badge`, for the deck and look-header
   buttons only.
3. Captioned looks become raised tiles, at most nine, and `all N ›` opens a
   plain list in the slot `Panel` (RA-27 §1.1, changes 3–4). Surprise me and
   vary this become secondary buttons with icons on their own row; blackout
   takes the danger tone; the deck becomes a region card.
4. One save in the look header, per the §4 B table. It replaces keep and the
   two-press header save, and `k` presses it. Today's `save…` editor stays as a
   tertiary `save as new…` until phase 2's menu.
5. h2, h3 and h4 in the heading role; the look panel a region card; the picked
   layer in the selected fill, its knobs indented 12; no hairlines there.
6. The deck, variety, layers and arm tests, and `docs/authoring.md`.

**Phase 2: B's structure.** Engine `undo` on the now line, and toasts. `Menu`,
then the look header moves into the frame. The path header, inspector and phone
push, with blackout on the phone's frame row (Decisions, item 7). The
remaining buttons (scan, blink, use for board, layout, health). ?
notes, label taps, the help sheet, `reason`, and the §3 words and signs. Then
the rest of the migration: root 100% with rem tokens; the other regions,
states and `modulated by` lines; old names deleted and grepped for (RA-27c
§3.8).

**Phase 3: scale.** Find, replacing `all N ›`; `move` and `rename`, then drag
and `move to key…`; what each look stores, in its menu; after the word test,
the engine strings, `catalog.md` and swatches.

## 8. Decisions for the maintainer

The maintainer's answers are in Decisions (2026-11-06), the first section.

1. **Build B?** Default: yes. Phase 1 doesn't wait on it. Decided: B.
2. **One one-press `save`,** replacing keep and the two-press header save, with
   save as new… under `▾`? Default: yes. Decided: yes.
3. **Undo instead of two presses, except blackout?** This is an engine request;
   `undo` waits on the now line until the next lossy act. Default: yes, in
   phase 2. Default taken.
4. **The words surprise me, vary this, brightness, shuffle, cues, step,
   modulators and main knobs?** Default: yes; the engine strings follow the
   word test. Decided: yes, with modulators for motion.
5. **Keys follow file order** (a look gets a key by moving into the first
   nine), not a pins list in the file (version 5)? Default: yes. Default
   taken.
6. **Move the look name out of the top bar on every device,** to the look
   header? It shows 3 times (A#8). Default: yes. Default taken.
7. **System sans for UI text, mono for keycaps and board addresses only?** It
   reverses the deliberate mono (`ui/theme.css:36`); mono reads worse and mixed
   faces blur hierarchy (RA-27c §3.1). Default: yes, in phase 1. Decided:
   Martian Grotesk and Martian Mono instead.

RA-27c's three smaller questions (its open questions 1–3) are settled:
blackout joins the frame row on a phone, which gives the editor 56 px
back (Decisions, item 7); the fade reads `fade: as saved`, the glossary's word
(item 3); and the page builds the warmer neutrals, the working value.

## 9. What changed from the draft

- **Refined:** save moves to the now line, the draft chip becomes a badge, find
  replaces the all-looks panel, and undo replaces confirms.
- **Replaced:** a list plus inspector replaces nesting in place
  [S1527][S1563], and find replaces WLED's "filter above 12". The WLED,
  Ableton and Chromatik evidence goes, so "shuffle" rests on Spotify [S1556],
  "palette" must pass the word test, and "a modulator shows both ends" is
  inference.
  RA-27 §9.4 resolves each item the draft tagged.
- **On the visual foundations** (RA-27c): §1, §6.2, the wireframe roles, phase
  1's tokens, and decision 7.
