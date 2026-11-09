# RA-27: Control-page UX

Last researched: 2026-11-06
Status: draft (every study is in; the maintainer's decisions are in RA-27b)
S-ID blocks: S1500–S1549 (S1500–S1537 used; S1538–S1549 free),
S1550–S1599, design-led (S1550–S1596 used), and S1650–S1699, modulator terms
(S1650–S1670 used). RA-27c uses S1600–S1649.

## The maintainer's direction

2026-11-05, verbatim:

> "I definitely wouldn't use WLED as an example for what to do for systems like
> this. very, very, amateur - engineer designed. we should borrow more for tools
> that have armies of ux designers and ux researchers to make things really
> thoughtfully usable. think spotify, Linear, figma, vercel, superhuman."

2026-11-06, after redesign phase 1b, verbatim (§11.2 quotes the first
sentence):

> "the font sizes we're using are a bit too big, and the padding everywhere is
> looking real funky. we can do better to make this look polished and
> pixel-perfect."

**The standing bar** for every page change and review. This is a paraphrase:
the build briefs for each page milestone and review loop stated it, and
the maintainer's own words for it were not kept. The page is clean, elegant and
design-led, with the calm of Linear, Vercel and Figma. It uses progressive
disclosure and minimal text: a one-line explanation only where a control is
not self-evident, and only on demand (a quiet ?, a tooltip, a long press),
never a wall of text. It is a solid UI on phone and desktop. §12 quotes the
maintainer's ask for a "very clear, concise tooltip or other progressive disclosure type
thing".

What this means for this doc:

- WLED is not a model. A recommendation that rested wholly or partly on WLED
  evidence carries `[NOT-A-MODEL]`, a greppable tag like
  `[NEEDS-VERIFICATION]`. The design-led study (§9.4) confirms, refines or
  replaces each one on other evidence. The WLED facts stay recorded as facts.
- Where §9 conflicts with an earlier item, §9 wins.

## Reading notes

- **Studies.** Eight study notes ran on 2026-11-05: looks-ia (`vj-led`,
  `patch`, `audit`, `proposal`), page-ia (`hierarchy`, `language`,
  `proposal`) and actions (`actions`). The design-led study (five product
  notes and a patterns note) ran the same day. This doc rewrites them all.
  [RA-27c](RA-27c-visual-foundations.md) holds the visual-foundations study
  (principles, a measured audit and the foundations spec), and
  [RA-27b](RA-27b-control-page-proposal.md) holds the final proposal built on
  it, pending the maintainer's choice of option.
- **Code facts describe commit 8853368 on branch `fx-ui-polish`.** That commit
  was not merged into `fx` on 2026-11-05, and the page is changing, so re-read
  a line before you build on it. Page paths are relative to `web/src/` and
  engine paths to `src/pewpew/`. A spot check of 20 cited lines against
  8853368 matched.
- **Screens.** The studies rendered the page with Playwright at 1440×900
  (desktop) and 390×844 (phone). Every page→engine message was dropped, so
  none was sent. The tree holds no binary assets, so the screenshots are not
  kept: the text says what each one showed.
- **Example data.** The engine ran `run wash` with a 12-look book (2 looks out
  of the idle cycle, no triggers, default cycle settings). The real looks are
  `warp-lane` (1 layer, 6 steps, 4 signals, 4 routes) and `firefly-ink` (one
  layer, `ink`, with the steps flies, bleed and tint). `tide` is illustrative,
  drawn from code and not rendered. Its layers, top first, are `sparks` (a
  pattern, screen 60%), `echo` (2 steps), `base` (5 steps: noise, kaleid,
  osc, fb, tint) and `wash`. Its routes are `breath` (lfo) → `base.osc.freq`
  ±0.2 and `bass` (band) → `sparks.opacity` ±0.4.
- "(inference)" marks the studies' own reasoning.

## Key questions

1. Why do saved looks and the make actions (surprise, like this, keep) read as
   one kind of thing? How do other tools keep recalling a saved item apart from
   doing an action? (§1.1, §2, §3, §6)
2. How should saved looks scale to 5, 50 and 500? (§1.1, §2, §6)
3. How should the page show what contains what: frame → look → layer → step →
   knob? (§1.2, §4, §7)
4. Which words should the page use, and how does someone learn more without
   hover or a tour? (§1.3, §8)
5. Which action hierarchy and which one shared button system should every
   control use? (§1.4, §10)
6. What do design-led products (Spotify, Linear, Figma, Vercel/Geist,
   Superhuman) do for each of the above? (§9)
7. What did the UI review loop find? (§11)
8. What common word names what moves the knobs, and how does one line explain
   it? (§12)

## Findings

### 1. The page at 8853368 (audit)

#### 1.1 Looks area

**What sits where.**

| | Phone (390×844) | Desktop (1440×900) |
|---|---|---|
| Deck order (`ui/deck/Deck.tsx:35`) | pinned bottom: looks row, variety row, master, cues, arm + BLACKOUT | top of the side panel: arm + BLACKOUT, master, looks grid, variety row + fade, cues |
| Editor slot (`app/App.tsx:98-107`) | scrolls above the deck | below the deck |

The slot holds, in order:
1. The look block: name, "revert", the fade (on a phone) and "save…".
2. The look editor, hidden until "save…" is pressed.
3. The look's own knobs.
4. "layers" with "+ layer". The catalog replaces the slot.
5. The picked layer's knobs.

- **Looks row** (`ui/deck/Looks.tsx`) recalls a saved look over the chosen
  fade. Marks: accent = live, dot = changed, ↻ = in the idle cycle (shown only
  when some look is out, `Looks.tsx:41`), dashed = a cue returns here,
  fill = a cue holds it, gradient = fading. Keys 1–9 recall the first nine
  looks (`Looks.tsx:28-39`). The empty state reads "No saved looks yet: name
  one in the look box and save it."
- **Variety** (`ui/deck/Variety.tsx`) acts on the running state, not on a saved
  look. "surprise" and "like this" play an unsaved look. That look shows only
  in the top bar and the look heading, never in the row
  (`domain/aura/aura.ts:58-63`). "keep" saves it under the engine's name
  ("surprise 7"), at the end of the row. The book is a dict, and a new name is
  inserted last (`aura/book.py:200-201`, `aura/looks.py:266-283`).
- **Look editor** (`ui/deck/LookEditor.tsx`) is in the slot, not the deck.
  Save, overwrite, delete and the ↻ box act on the name typed in the box, which
  follows the current look, so deleting another look means typing its name.
  That makes two ways to save, in two places: "keep" (in the deck; the engine
  names the look) and "save…" (in the slot; you name it).
- **Cycle** is a per-look flag, set only in the editor. An "IDLE CYCLE" tag
  shows while it runs (`ui/status/TopBar.tsx:39-48`). Its settings are file-only.
- **Triggers and cues:** the page shows trigger names and the arm switch. It
  never edits triggers (`aura/book.py:72-74`), and a cue's look shows only
  once the cue fires (`aura/triggers.py:206-218`).
- **Layers** are the live state. An edit marks the current look changed until
  "save…" or "keep".

**Why "surprise" and "like this" read as presets.**

1. **Same style.** Looks and variety buttons share the zero-specificity base
   button rule (`ui/theme.css:109-121`). The computed styles of a look and of
   "like this" are identical: a 1px `rgb(96,96,106)` border, a transparent
   background, a 4px radius, weight 400, and a height of 24px on desktop and
   44px on a phone. Only "surprise" differs (`.primary`: fill and bold,
   `theme.css:156-160`). That makes it the loudest button in the deck, louder
   than the live look.
2. **Same container, same gap.** `Deck.tsx:19-24` wraps `<Looks>` and
   `<Variety>` in one `.looks-row` column with a 0.4rem gap
   (`theme.css:727-731`). The scroller uses the same gap (`theme.css:224-230`).
   The last look sits 5px from "surprise" on desktop and 6px on a phone, the
   same as the line gap inside the wrapped grid. On desktop the variety row
   reads as the grid's last line.
3. **No visible caption.** Each group has only an aria-label ("saved looks",
   "made looks"). Master and cues have a visible `.cap` label
   (`ui/deck/Master.tsx:35`, `ui/deck/Cues.tsx:11`).
4. **Overloaded marks.** Dashed means off (keep disabled, `theme.css:136-140`)
   and also marks the look the lights return to after a cue
   (`theme.css:719-722`).
5. **Phone.** The variety buttons stretch (`flex: 1 1 auto`,
   `theme.css:756-759`) into wide boxes like look tiles. With the editor open,
   its name field is a bordered box of the same size (phone screenshot, save
   open).
6. **Shared "?".** The "?" on the variety row also explains the looks row's
   marks (`Variety.tsx:12-16`).

**Cardinality.** The hard limit is 64 looks (`MAX_LOOKS`, `aura/book.py:104`).
The loader refuses a file with more (`book.py:252-253`), and saving a 65th is
refused with "there are already 64 looks; delete one first"
(`aura/looks.py:297-298`). The 200-look case below was rendered with
`looks.items` padded in the browser, so it shows only the page.

| Looks | Desktop (side panel 516px) | Phone | Keys |
|---|---|---|---|
| 3 | 1 line, deck 128px | 1 row, content 452px wide in a 358px view | 1–3 |
| 12 (real) | 4 lines, deck 216px, slot 652px | content 1,729px wide, about 2 names in view | 1–9; looks 10–12 have none |
| 50 | 12 lines, deck 420px, slot 448px | 5,781px (about 16 screens) | 1–9 |
| 64 | 15 lines, deck 508px, slot 360px: the knobs get 40% of the height | 7,277px (about 20 screens) | 1–9 |
| 200 (page only) | the deck stops at 60% and scrolls inside, which pushes surprise, like this and keep out of view | 22,728px | 1–9 |

- **Keys 1–9** recall the first nine looks in file order. The page cannot
  reorder looks: `REQUESTS` has `move_layer` but nothing for looks
  (`aura/control.py:75-95`). New saves and keeps go at the end, and an
  overwrite keeps its place. A rename is a save-as plus a delete, so the look
  moves to the end and loses its key. The operator cannot choose from the page
  which looks get keys.
- **Phone:** the looks are always one swiped row. It wraps only on a wide
  screen with a fine pointer (`theme.css:245-250`). The live look scrolls into
  view; reaching any other look means swiping.
- **Performance is not the limit.** The state sends only the name and the cycle
  flag per look (`aura/looks.py:188`). Rendering every button is fine at 64
  (inference). Every recall rewrites and fsyncs the whole file on the loop
  thread (`aura/looks.py:513`). Measured: 0.57 ms for 33 KB at 12 looks, and
  1.22 ms for 178 KB at 64.

**In the data model but not on the page.**

- **Fade per look** (`fx/codec.py:76`). The "fade: saved" choice uses it, but
  the page never shows it. It is set only at save time, through the fade
  picker; "saved" keeps the old fade (`aura/looks.py:255`).
- **Master per look**, stored or not: the "include master" box at save time.
  The page never shows it afterwards.
- **Cycle settings:** `idle`, `each` (a number or a range), `rounds`, `end`,
  `window`, `fresh` (every nth slot plays a new made look), `seed`, and
  per-look `weights` (`aura/book.py:30-31, 51-61`). None of these is sent in
  the state (`aura/looks.py:181-199`), and none can be edited on the page.
- **Triggers** (look, hold, priority, debounce, cooldown): file only.
- **`notes`:** one free value for the whole file, written back unchanged
  (`aura/book.py:192`). Looks have no notes of their own.
- **Made looks:** only the one playing (`made`). Each made look keeps its seed
  (`aura/variety.py:8-12`), and `surprise` and `vary` accept a seed
  (`infra/wire/protocol.ts:150-153`). So a "recent made" history could be a
  list of seeds. A replay matches on the same map, because the surprise
  generator takes only the seed, the mapping and the grouping
  (`aura/variety.py:74`) (inference).

Not in the model: tags, banks, favourites, per-look notes, thumbnails, ordering
and rename. `LOOK_KEYS` is strict (`fx/codec.py:76`, refused at
`fx/codec.py:141`). So any new per-look key needs a codec change, and older
engines would refuse files that use it. Names allow only letters, digits,
space, `_` and `-` (`aura/book.py:108`), so a prefix convention cannot use `/`
or `:`.

**The audit's smallest structural changes, in order:**
1. Separate the actions from the looks. This is CSS plus one caption, with no
   engine change. Style the variety buttons as actions, drop `.primary` from
   "surprise", add a visible "looks" caption, put a real separator (twice the
   grid gap, or a hairline), and give "off" its own mark.
2. One save area: move "keep" next to "save…", or fold surprise, like this and
   keep into one "make" control.
3. Bound the deck on desktop: cap the looks grid at a few lines, with inner
   scroll or a "more" button.
4. Add a "looks…" panel on the phone, using the slot `Panel` pattern
   (`ui/common/Panel.tsx`, as `AddLayerPanel` does). The deck row keeps the
   nine keyed looks.
5. Add order and rename requests: a `move_look` that mirrors `move_layer`, and
   a rename that keeps the look's place.
6. Show what each look stores: send fade, stored master and cycle weight in
   `state()` (`aura/looks.py:188`).
7. Only then add tags or banks, which need the codec change above.

#### 1.2 Nesting and visual hierarchy

The page has five levels: frame → look → layer → step → knob. The slot renders
them as three sibling blocks under the deck: the look, the layers, and the
picked layer's knobs (`app/App.tsx:98-107`).

| Thing | Belongs to | Where it shows at 8853368 |
|---|---|---|
| Front knobs | the look (each is some layer's knob) | top of the look block, with no heading; the owner is named only when there is more than one layer (`contextsOf`) |
| Signals | the look | the look block, one fold each, titled `motion · <id>` |
| Routes | the look | a sentence under the target knob ("moves with pulse, ±0.5") and a live mark |
| on / opacity / blend / order | the layer | the row head (switch, glance) and the open row body |
| Steps and their knobs | the layer | a separate block *below the whole list*, titled `layer <id>` |

Problems:

1. **A layer's knobs are not inside the layer.** The row body holds the mix,
   and the knobs follow the whole list (`app/App.tsx:102-104`). So picking row
   2 of 4 puts its knobs under rows 3 and 4. On touch the rows start closed,
   yet the top layer's knobs still show (`ui/stack/selection.ts:26`).
2. **Front knobs read as the look's own.** With one layer they name no owner,
   and `frontFirst` (`domain/stack/stack.ts:142`) removes them from their step.
   So `fb · feedback` lacks zoom and decay.
3. **Modulation is one-sided.** A signal never lists what it moves; only the
   target says.
4. **One indent for three relationships.** The accordion rail
   (`ui/theme.css:1018`) wraps signal knobs, a layer's body and step knobs
   alike, so all three read as one depth.
5. **Flat surface, with one hairline everywhere.** Five element types share
   `border-top: 1px var(--line)` on `--bg`. On the phone, `warp-lane` renders
   as about 60 rows in the same rhythm.
6. **Inverted type scale.** Block headings are 0.85em and muted, smaller than
   the step titles and knob labels under them (1em, muted).
7. **Amber means eight things:** the current look, the picked layer, the reset
   dot, a switch, a segment, the live mark, IDLE CYCLE and focus. So it cannot
   mark the layer being edited.
8. **Flat heading tree.** There are three `h2`s. Rows and folds are bare
   buttons (inference from `ItemTrigger` use), so assistive tech gets no
   nesting. WCAG 2.2 SC 1.3.1 asks for visual relationships to be programmatic
   [S1531].
9. **Deck:** saved looks and surprise / like this / keep share one bordered
   style (§1.1).

#### 1.3 Words and help

1. **One thing, two words.** "triggers: off / ARMED" switches what "cues (arm
   first)" fires (`ui/deck/Triggers.tsx:20`, `ui/deck/Cues.tsx:11`). "like
   this" makes a look named "variation 2" (`aura/variety.py:97`). Titles say
   "recall".
2. **One sign, two meanings.** The accent dot means "look changed since saved"
   (`ui/theme.css:313,700`) and also "knob off its default, tap to reset"
   (`theme.css:953`). While a saved look plays, every front knob carries it.
   "?" opens shortcuts in the top bar (`ui/status/TopBar.tsx:65`) but explains
   things in the deck (`ui/deck/Variety.tsx:96`).
3. **Code names on the page.** "params" (`ui/params/ParamPanel.tsx:96`),
   "custom · 3 steps" (`domain/stack/stack.ts:185`), and the shelves "space"
   and "combine two fields" (`domain/stack/catalog.ts:42`). Cards are named
   "geq" and "sdf3d". The "more ▸" buttons read
   `osc(3, 0.15, axis="u").palette("ocean")` (`ui/stack/AddLayer.tsx:126`).
   Knob captions default to the argument name, capitalised
   (`params/kinds.py:84`), which is why some knobs read Freq, Gain or Attack.
   A macro's front knob reads "value · macro" (`domain/stack/stack.ts:87`).
   That last one is inference, because the live look has no macro.
   *Correction (page-ia proposal):* osc's `sync`, Hydra's name for that
   argument [S1400], already reads "Drift" (`fx/ops/source.py:57`). The
   language study had said it showed as "Sync".
4. **"like this" reads as a Like button** (inference). It has no verb, which is
   part of why it reads as one of the preset chips.
5. **Help lives in three places:** the "?" toggle, a focus-only overlay for knob
   help (`ui/theme.css:927-943`), and `title` attributes. The `title` text
   carries real reasons ("firefly-ink is already saved"), and phones never show
   it [S1524].
6. **Headings don't say who owns what.** The look name, "layers" and "layer
   ink" are all `h2`. No word says that ink belongs to firefly-ink, or that the
   knobs under the look name are borrowed from a layer.

#### 1.4 Actions and buttons

All buttons share one base rule in `ui/theme.css`: a 1px `--line-strong`
outline and a minimum size of `--target`, which is 24px for a fine pointer and
44px for a coarse one. The modifiers are:

- `.quiet`: muted text, no border.
- `.primary`: grey fill and bold. Only `surprise` has it.
- `[aria-pressed]`: an amber outline.
- `[data-armed]`: a red fill.
- `[data-pending]` and disabled: a dashed border.

There are few shared parts: `TwoTapButton` (`ui/common/TwoTapButton.tsx`),
`AboutButton` (`quiet about`, `ui/common/AboutButton.tsx`) and the `PanelHead`
✕. Everything else is about 20 raw `<button>`s.

| Element | At 8853368: component · look | Real role |
|---|---|---|
| surprise | TwoTapButton `.primary` · grey fill | deck primary |
| like this | TwoTapButton · outline | secondary |
| keep | TwoTapButton · outline | commit (= save) |
| saved look | `.look` · outline; the live one has an amber outline | selection item |
| save… | `.quiet` · muted; its open state is not drawn | disclosure to a form |
| save / overwrite | TwoTapButton · outline | the form's commit |
| delete, remove | TwoTapButton `.quiet` | destructive |
| revert, reset all | TwoTapButton `.quiet` | lossy, rarely used |
| include master | checkbox | form option, applied on save |
| in idle cycle | checkbox that sends at once | immediate setting |
| layer on, bool knobs | checkbox drawn as a switch | immediate setting |
| + layer | `.quiet`, aria-disabled with a title when full | opens a panel |
| ▲ ▼, master − + | raw · outline | secondary icon / stepper |
| replace with pattern…, more ▸, ? | `.quiet` / AboutButton (aria-pressed) | disclosure |
| ✕, ? shortcuts | `.quiet` | close / open a dialog |
| blackout | TwoTapButton · red outline, bold capitals | danger toggle |
| triggers arm | TwoTapButton aria-pressed · solid amber when on | toggle |
| cues | `.cue` · outline, disabled until armed | momentary action |
| pattern picks, segments | Ark ToggleGroup (amber outline) / SegmentGroup (solid amber) | selection |
| catalog card, + example | `.card-add` outline / `.quiet` | add |
| add / remove stop | `.quiet` | secondary / destructive |
| layout, input ends, single-key shortcuts | raw aria-pressed | toggle |
| scan, blink, use for board | raw / TwoTapButton · outline | the panel's main action |
| reset dot, health chip, tags, banner | own styles | state with an action attached |

Where it breaks:

1. **Save comes in three forms that look different:** `keep` (deck, outline),
   `save…` (header, muted text) and `save`/`overwrite` (editor, outline). The
   header button is the changed look's main commit. Yet it has the page's
   lowest emphasis: `.quiet`, like delete and ✕, and the muted grey of labels.
   On the phone, "layers" and "+ layer" look identical (phone screenshot,
   layers). With weak signifiers, NN/g measured tasks taking 22% longer, and
   "click uncertainty" [S1525]. Once open, `save…` does not look open. Saving
   your edits to the current look is labelled "overwrite", takes two presses
   and turns red, so the everyday save looks dangerous.
2. **Actions look like items.** Saved looks, like this, keep, cues, cards, ▲▼,
   steppers and pattern picks share one outline style. Apple: "Don't assign
   actions to segments in a control that otherwise represents selection state"
   [S1521]. Material treats chips as a set of items, distinct from buttons
   [S1523].
3. **The hierarchy is upside down.** The live look (amber outline) and armed
   triggers (solid amber, bold) outshine the grey primary.
4. **Destructive actions don't look destructive.** Delete and remove are muted
   text until armed.
5. **Toggles come in four looks:** switch, checkbox, amber-outline button and
   solid-amber button. "In idle cycle" acts at once, yet it sits beside
   "include master", which waits for save. NN/g says this mix "confuses users"
   [S1526].
6. **Dashed means three things:** off, pending, and the look the lights
   return to after the cue.
7. **"Off" is handled three ways:** native `disabled`, `aria-disabled` with a
   title, and `aria-disabled` where a press shows the reason (Variety). GOV.UK
   warns that disabled buttons "can confuse some users, so avoid them if
   possible" [S1534]. Variety's way is the one to keep.

### 2. Prior art: saved items in VJ, LED and lighting tools

How these tools show 5, 50 and 500 saved items, and how they keep recalling a
saved item apart from doing an action.

- **Resolume Arena.** Clips sit in a grid of layers (rows) and columns, and a
  click on a clip's thumbnail fires it. Each clip has a thumbnail (the current
  frame or an image) and an optional pastel colour. A column fires every clip
  in it at once, "to switch between looks that work well together" [S1500].
  Decks group the grid "like the records in a DJ's record bag". You pick a deck
  from a button row below the layers, and decks can be named, colour-coded and
  closed without being deleted [S1500]. Persistent clips keep their slot in
  every deck [S1500]. Since 7.22, selecting a column no longer fires it: a
  separate play button does [S1501]. A heart favourites an effect or source,
  and favourites rise to the top of the lists [S1501].
- **MilkDrop.** The library is a folder of thousands of preset files, and the
  performer seldom browses it. The docs centre on random and next traversal.
  Ratings from 0 to 5 "decide how often the presets will be randomly loaded",
  and a rating of 0 keeps a preset out of random play [S1502]. L opens a load
  menu for a deliberate pick, and BACKSPACE steps back through up to 64 recent
  presets [S1502]. Scroll Lock pins the current preset against random
  switching. Space blends to the next preset and H hard-cuts [S1502]. A mashes
  two random presets' shaders into a new one, and S saves it [S1502]. Actions
  are keys and presets live in the browser, so no preset is ever a button.
- **Pixelblaze.** The Patterns tab lists every pattern with a preview image.
  Next, Shuffle All and Playlist modes sit in a separate sequencer bar, and
  each row's Add button puts the pattern on the playlist for 30 s by default
  [S552]. This comes from the client's reverse-engineered protocol document,
  not from ElectroMage. Playlist entries can be dragged into order
  [S405][NEEDS-VERIFICATION], read from a search snippet only, because the
  page returned 403.
- **WLED.** The UI source was read directly [S1503:wled00/data/index.htm]
  [S1503:wled00/data/index.js]. Read top to bottom, the Presets tab has four
  parts:
  1. A "Quick load" row of small round buttons. Each preset can carry a label
     of up to 2 characters or 1 emoji, shown "in a small circle on top of the
     preset list for extra quick access without scrolling" [S554][S1503].
  2. A sticky search box that filters the list [S1503].
  3. The list. Playlists sort first and carry a play icon, and the startup
     preset has its own icon. Each row has an edit pencil and an expand arrow,
     and the list sorts by name or by ID [S1503].
  4. A bottom bar with "+ Preset" and "+ Playlist", styled unlike the rows
     [S1503].

  The editor offers "use current state" or "overwrite with state", Save and
  Delete, and IDs from 1 to 250 [S554][S1503]. The docs advise about 50
  presets at most, for responsiveness [S554]. Because the list sorts by name,
  users force an order with numeric name prefixes [S1505].
- **Chromatik (LX).** Snapshots are a list with a + button. Each row has a
  label, a Recall button (→) and a Cycle checkbox, and its right-click menu
  offers Update (overwrite) and a per-snapshot Cycle Time [S1265]. Auto-Cycle
  has two modes: Next, and Random without repeating the current snapshot. Only
  snapshots with Cycle on take part [S1265]. A transition time and a "Snapshot
  Contents" filter apply to the whole list [S1265]. Device presets are files
  saved from a right-click menu [S1506], and there is a clip-grid mode [S1265].
  pewpew's per-look "in the idle cycle" toggle maps one to one onto Chromatik's
  Cycle checkbox (inference).
- **MadMapper.** Scenes sit in a table of cells. A + in an empty cell makes
  one, and a gear sets its colour and fade [S1507]. Columns play once, in a
  loop or at random [S1507]. A scene stores everything, and a cue stores only
  chosen parameters [S1507]. This is a community guide, not GarageCube's docs.
- **grandMA3, ChamSys and Onyx** all keep stored objects apart from the controls
  that fire them.
  - grandMA3 executors are "handles and controls to other objects", and the
    sequences they fire live in a pool. There can be up to 9,999 executor pages
    [S1508]. Pool windows are numbered grids with labels, appearances (colour or
    image) and a "Show Empty" toggle, and Store with no number fills the first
    free slot [S1508]. Verbs such as Store, Edit and Delete are hardware keys,
    never pool tiles [S1508].
  - ChamSys's Execute window is a user-designed grid of up to 40×40 cells. It
    mixes stored items with "special items" such as Exec Page Up/Down, Release
    and Clear [S1509]. Separate Design and Execute views keep arranging apart
    from playing. A "Coloured" appearance colours buttons by function, and a
    common setup is a Home grid of page-jump buttons [S1509].
  - Onyx has 500 named banks of 10 playbacks, and a swipe changes bank
    [S1510]. It has 100 pages of 10×10 virtual buttons. On those you choose the
    verb first (Go, Release, Select) and then the cuelist [S1510]. The Cuelist
    Directory is the store, with grid and list views and live status on each
    tile. Playback controls only point into it, and a cuelist's colour shows
    everywhere it appears [S1510]. Only one cuelist can be selected, and
    selecting it does not run it [S1510].
- **TouchDesigner and Notch:** a built-in preset browser was not found.

**How the tools scale (inference from the above):**

| Count | Common shape |
|---|---|
| ~5 | A flat row or grid of named tiles, plus number keys (WLED quick load, MilkDrop hotkeys, one Resolume column) |
| ~50 | One scrolling list or grid, with search, colour and one-tap recall; order kept by a manual sort or name prefixes (WLED, Chromatik snapshots, a Resolume deck) |
| ~500 | A store (pool, directory or folder) apart from a curated performance surface (pages, banks or decks), plus weighted random for discovery (grandMA3, Onyx, Resolume decks, MilkDrop ratings) |

**Transferable patterns (inference, each resting on the cites given):**

1. **Verbs and nouns look different and sit apart.** WLED pins its add buttons
   to a bottom bar [S1503]. Consoles put verbs on keys or a mode bar and keep
   stored objects in the grid [S1508][S1510]. ChamSys mixes the two only behind
   a colour-by-function scheme [S1509]. For pewpew, "surprise", "like this" and
   "keep" are generators and "save…" is a verb, so they belong in a toolbar
   with icons, apart from the look tiles. `[NOT-A-MODEL]` applies to the WLED
   evidence only; the console evidence stands, and §9.4 confirms the pattern.
2. **A small pinned set, then the full library.** WLED's quick-load circles sit
   above a searchable list [S554][S1503], and Resolume's favourites rise to the
   top [S1501]. This maps onto keys 1–9: let the performer pin up to 9 looks and
   show those first. `[NOT-A-MODEL]` (§9.4 refines it: the first nine, with full
   names and keys)
3. **Search only for long lists.** WLED's search box is sticky [S1503]. pewpew
   could show it only above about 12 looks. `[NOT-A-MODEL]` (WLED was the only
   evidence; §9.4 replaces it with find, from the first look)
4. **Cycle membership is a per-item toggle, and the cycle has a mode.**
   Chromatik's Cycle checkbox with Next/Random auto-cycle [S1265], and
   MilkDrop's ratings [S1502], both match pewpew's idle director. A weight
   could later replace the on/off toggle.
5. **Selecting is not firing.** Resolume 7.22 split selecting a column from
   firing it [S1501], and selecting an Onyx cuelist does not run it [S1510].
   pewpew already recalls on a tap, so editing should open from a separate
   affordance, such as a long press or an edit mode, never from the tap.
6. **Hold the current look, and go back.** MilkDrop's lock and 64-step history
   [S1502] suit live use. pewpew could add "undo last surprise" or "previous
   look".
7. **Group past about 30 looks.** Decks and banks are named and coloured, and
   switched by tab or swipe [S1500][S1510]. For pewpew one tag or "book" chip
   row would do; full pages are needed only at console scale.
8. **Generators feed the library.** MilkDrop's A (mash) then S (save) [S1502]
   matches pewpew's surprise then keep. The unsaved result could show as a
   draft tile at the start of the row.

### 3. Prior art: preset browsers and pattern libraries

- **Ableton Live 12 browser.** Collections are colour labels: keys 1–7 assign
  them, 0 clears, and clicking a label in the sidebar lists every item with that
  colour [S1512]. Tags come in groups. Users add their own through the Tag
  Editor or Quick Tags (with autocomplete), and Ctrl/Cmd-click selects several
  tags in one group [S1512]. With Preview on, the arrow keys audition items;
  cueing a preview to headphones needs extra outputs [S1512]. In Similarity
  Search, a "Show Similar Files" icon appears next to the selected file. The
  results sit under the reference file, from most to least similar [S1512].
  This is the closest analogue to "like this".
- **Native Instruments Komplete Kontrol.** A star appears on a preset when it is
  hovered or selected, and an icon in the search field filters to Favorites
  [S1513]. Sound Type is a two-level hierarchy (Type, then Subtype) and matches
  any selected tag, while Character tags must all match [S1513]. One click
  auditions a preset without loading it, a double-click loads it, and the arrow
  keys step through the list [S1513]. A random control was not found.
- **Synth browsers and random:**
  - Arturia Analog Lab's shuffle icon in the preset-list header reorders the
    list and does not load a preset. A user asked for a separate "dice button
    that randomly selects a preset". Its playlists hold sounds for instant
    recall by program change [S1514].
  - Minimal Audio Eprom's browser has a Random button that "loads a randomly
    selected preset instantly", a Heart for favourites, and category filters
    [S1514].
  - A community Synplant 2 browser's random button "jumps to a random preset,
    respecting the active filter", with a star per row and a Favorites-only
    view [S1514].
  - Vital and Serum 2 have no random preset loader, per a Substack post, and
    Vital users ask for one. Serum 2's `< >` arrows step through the current
    subfolder without opening the menu [S1514].
  - Where a random button exists, it lives in the browser chrome (the list
    header or the toolbar), not among the presets [S1514]. No product was found
    that puts random among the preset items.
- **Lightroom** (third-party sources, since Adobe's help returned 403):
  - Moving the cursor over a preset thumbnail previews it on the photo, and a
    preference turns this off [S1515].
  - The Recommended tab offers a "More like this" button on hover, which "will
    filter the presets down further" [S1515]. That makes "more like this" a
    per-item action.
  - A starred profile appears in a Favorites folder at the top of the browser,
    and in the Basic panel's drop-down [S1515].
  - Manage Presets hides unused groups [S1515].
- **Procreate brush library.** The Recent set fills itself with up to eight
  brushes, and a brush can be pinned there [S1516]. Each brush row previews "the
  stroke it makes" [S1516]. You can create sets, drag brushes and sets into a
  new order, and swipe to duplicate a brush [S1516].
- **Instagram filters.** A Manage item with a gear icon sits at the end of the
  filter row. It opens a screen where you drag filters into a new order and
  uncheck the ones to hide [S1517]. These are third-party guides, and the
  current app may differ.
- **Hardware recall (live use).**
  - Roland XPS-60: hold FAVORITE and press one of [1]–[16] to store a scene.
    There are 16 banks of 16 slots ("Favorite 256") [S1518]. An asterisk marks
    an edited, unsaved scene, which must be saved before it can be stored. In
    another mode the same 16 buttons select tone categories [S1518].
  - Line 6 Helix: 8 setlists of 128 presets. FS1 and FS7 step banks, and a
    global setting makes them step single presets [S1519].
- **Game saves.** Starsector's autosave rotates through three labelled slots and
  "will NEVER overwrite a manually-created save slot". Several quicksave slots
  were rejected as clutter [S1520][NEEDS-VERIFICATION]. This was read from a
  search excerpt only.

**Transferable patterns (inference):**

1. **Nouns and verbs look different.** Saved looks are selectable items: lit
   when live, never icon-led. Surprise, like this and keep form a separate
   cluster with an icon and a short label, such as a die for surprise and a
   branch for like this. The cluster sits at a fixed end of the strip or in the
   top bar, never inside the scroller. Eprom and Analog Lab put random in the
   browser chrome, not in the list [S1514].
2. **An unsaved look shows as a draft.** A surprise or variation appears as a
   provisional item at the head of the row, with a dashed outline and an
   asterisk like Roland's [S1518], and it carries its own keep. Keep stays off
   until there is a draft, which fits the existing `keepReason`
   (`domain/aura/looks.ts:75`).
3. **"Like this" acts on an item,** following Lightroom's More like this
   [S1515] and Ableton's Show Similar [S1512]. Put it on the live look, or
   offer it from any look on long-press. It then reads as "vary this", not as
   another look.
4. **Random can respect the current scope:** surprise within a selected tag or
   bank, as the Synplant browser does [S1514].
5. **Scale in tiers, with two disclosure levels at most** [S1524]:
   - Up to about 9 looks: one row, keys 1–9 (as at 8853368).
   - About 10–40: banks of 9, with keys 1–9 recalling within the current bank
     and a bank stepper, like Roland's 16×16 [S1518] and Helix's banks [S1519].
     Or a setlist: a curated, ordered subset separate from the library,
     like Helix setlists or Analog Lab playlists [S1519][S1514].
   - Beyond that, the row shows only favourites or the setlist. A library sheet
     (a bottom sheet on a phone, a side panel on desktop) adds
     search-as-you-type, starred favourites, tag filter chips [S1512][S1513],
     and an automatic Recent set of 8 [S1516].
6. **Previews instead of names.** Give each look a small swatch or strip of its
   colours or motion, like Procreate's stroke previews [S1516] and Lightroom's
   thumbnails [S1515]. The render core can draw these deterministically. While
   the lights run, preview on the page first and then commit to the rig, like Komplete
   Kontrol's audition-then-load [S1513] and Ableton's cue output [S1512].
7. **Manage at the end of the row.** Reordering and hiding go behind a gear at
   the end of the row, like Instagram's Manage [S1517], or behind a long press,
   like the HIG's touch-and-hold to edit [S1522]. The ↻ idle-cycle flag can
   live there too.
8. **Made looks don't vanish.** Unkept surprises go into a short rotating
   history that never overwrites saved looks, like Starsector's autosaves
   [S1520] and Procreate's Recent [S1516].
9. **The empty state offers a path:** a surprise button and "or save the
   current look", not only a sentence [S1524].

Not found: official Serum 2 or Vital docs on favourites or random. The
m3.material.io pages did not render.

### 4. Prior art: stacks with children

- **Figma:** the right sidebar shows controls for the selected layer, and page
  and file options when nothing is selected. A layer's blend is in the
  sidebar's Appearance section [S1527].
- **Resolume:** each layer strip has blend and opacity. Clicking a layer's name
  highlights it and opens Layer Properties, whose Blend Mode and Opacity "match
  the layer strip controls" [S1500]. Effects sit at clip, layer/group and
  composition level [S1500].
- **Ableton racks:** contents are "always contained between end brackets", so
  a nested rack shows as brackets within brackets [S1512]. The chain list
  selection drives the devices view. Macros are a bank of 8–16 knobs mapped to
  any parameter in the rack, and Map mode shows a coloured overlay on mappable
  parameters [S1512].
- **Chromatik:** each channel has its own device bin, and a line marks the
  focused channel. A separator splits pattern effects from channel effects,
  which can't be reordered across it [S1506]. Modulation is drawn on the knob
  in the source's colour, and "Show Modulation" jumps to the mapping. Each
  modulator lists its mappings with their range [S1265].
- **Blender:** one collapsible panel per modifier, run top to bottom, with the
  active one outlined [S1528].
- **TouchDesigner:** the parameter dialog's header names the operator, and its
  parameters are split into pages [S1529].
- **Apple HIG:** an inspector "displays the details of the currently selected
  item". A sidebar shows at most two levels, and deeper needs a split view. An
  outline view keeps people's expansion choices [S1522].
- **NN/g:** a boundary "can overpower" proximity and similarity, but too many
  borders clutter [S1525]. Beyond two levels of disclosure, "users often get
  lost" [S1524]. Long open accordion sections on a phone need a sticky header
  [S1525]. Use about three type sizes and at most three contrast variations
  [S1525].
- **Material 3:** surface container roles run from lowest to highest emphasis
  and are no longer tied to elevation [S1523][NEEDS-VERIFICATION]. This was
  read from a search snippet only.
- **W3C:** wrap each accordion button in a heading with a fitting `aria-level`
  [S1530], and make visual relationships programmatic (SC 1.3.1) [S1531].
- Not checked: Lightroom solo mode (Adobe's help returned 403), Logic channel
  strips, and Notch.

What they share (inference): a layer's controls sit inside it, or in an
inspector named for it. The mix shows twice: a glance on the row, and in full
when the row is open. Modulation shows on the target in the source's colour,
and the source lists its targets.

### 5. Guidelines: selection, disclosure and empty states

- **Keep actions and selection apart.** Apple: "Don't assign actions to
  segments in a control that otherwise represents selection state." Apple
  also recommends at most about 5 segments on iPhone [S1521]. The looks row
  works as a selection control, because one look is lit. So verbs inside it,
  or styled like it, break this rule (inference).
- **Material 3 chips.** Assist chips are for actions and should "appear
  dynamically and contextually", filter chips narrow content, and buttons keep
  one consistent look [S1523].
- **Split button.** Its leading part runs the main action, and its trailing part
  opens related actions [S1523].
- **Collections and lists.** Collections suit images, and text reads better in
  a list. The defaults are tap to select and touch-and-hold to edit [S1522].
- **Mobile carousels.** Users should reach the last item in "3–4 steps", and a
  long set needs a list view. A partly visible next item is "a strong carousel
  cue" [S1525].
- **Progressive disclosure.** Designs with more than two disclosure levels
  "typically have low usability" [S1524].
- **Empty states** show system status, give learning cues, and offer "direct
  pathways" to the key task [S1524].

### 6. Saved looks: diagnosis, options and recommendation (looks-ia)

**Diagnosis.** The looks are not hard-coded. They come from the looks file
passed with `--looks` (the `aura/book.py` docstring). "keep" saves a made look
under the engine's name, and "save…" saves under a name you type. The file holds
at most 64 looks, and every new look goes to the end. Keys 1–9 recall the first
nine in file order, and the page cannot reorder looks (§1.1).

What is unclear, and why:
1. **Nouns and verbs look the same** (§1.1, the "read as presets" list).
2. **A made look has nowhere to live.** "surprise" plays a look that appears only
   in the top bar and the look heading (`domain/aura/aura.ts:58-63`). So "keep"
   acts on something you cannot see as an item, and the rest of the time it
   sits as a dashed ghost, and dashed also means "a cue returns here".
3. **Two ways to save, in two places.** The idle-cycle flag is set only in the
   editor.
4. **No structure past a handful.** At 64 looks the desktop grid takes 15
   lines, and on a phone the row is about 20 screens long. Order is the only
   structure, and you cannot see or change it.

The root cause: the page draws nouns and verbs with one grammar, the bordered
box, and it shows nothing about which looks matter.

**What all three options share:**

- **Verbs sit in the list's chrome, not among the items.** The evidence is the
  HIG rule [S1521], WLED's bottom bar [S1503], and Eprom's Random and Analog
  Lab's shuffle in the browser header [S1514]. pewpew already has a verb style,
  `button.quiet` (borderless, muted, `ui/theme.css:148`), on "save…", "+ layer",
  "remove" and "reset all". So the make verbs move into the looks header line
  in that style, and the row holds only looks. `[NOT-A-MODEL]` applies to the
  WLED evidence only; §9.4 confirms the pattern. The actions study (§10) and
  RA-27b replace the quiet style with real buttons.
- **The made look is a draft item.** Roland marks an edited, unsaved scene
  with an asterisk [S1518]. MilkDrop mashes with A and saves with S [S1502].
  So while a made look plays, a draft tile leads the row: lit, with its name in
  italics and "keep" as its trailing segment, like a split button [S1523]. With
  no draft there is no keep, so there is no dead button. The state already
  sends `made` (`aura/looks.py:198`).
- **Two levels of disclosure at most** [S1524]: the deck, then one panel.
- **A tap recalls, and editing is a separate mode.** The HIG uses
  touch-and-hold to edit [S1522], and Resolume 7.22 split selecting a column
  from firing it [S1501]. Organizing never happens on the deck (inference: a
  mid-run rearrange must not be one stray drag away).

Shared deck header (phone, 358px):

```
looks              ⚄ surprise  ≈ like this  ?
[⁎surprise 7 · keep][dusk][tide][ember]…
```

The glyphs are optional; check that they render in the page's mono font.

#### Option A: set and library

**Model.** The first nine looks are your **set**: they sit on the deck, and keys
1–9 recall them. The others are in the **library**, one tap away. You choose
the set by arranging the order.

```
PHONE, 5 looks                     PHONE, 50 looks
looks      ⚄ surprise ≈ like this  looks   ⚄ surprise ≈ like this  50›
[dusk][tide][ember][prism][warp]   [dusk][tide][ember][prism]…  (9 + live)
master ──────●──── 70%             master ──────●──── 70%
[         BLACKOUT          ]      [         BLACKOUT          ]

LIBRARY PANEL ("50›"; the slot Panel, as "+ layer" uses)
looks                    arrange  ×
[ filter…                       ]     (shown above 12 looks)
1 dusk     2 tide     3 ember
4 prism    5 warp     6 lantern
7 ink      8 bloom    9 lagoon
──────────────────────────────────
copper     depth      fountain   …

DESKTOP, 50 looks (side panel)
looks   fade: saved ▾          ⚄ surprise  ≈ like this  ?
[dusk¹][tide²][ember³][prism⁴][warp⁵]
[lantern⁶][ink⁷][bloom⁸][lagoon⁹]                  all 50 ›
```

- **5 looks:** no library link. The row holds everything, and every look has a
  key.
- **50 looks:** the deck shows at most nine tiles, plus the live look when it is
  outside the set, so a look you just kept never vanishes. The library is a
  grid with a name filter, shown above 12 looks. `[NOT-A-MODEL]` (the threshold
  came from WLED's search box, §2 pattern 3; §9.4 replaces it with find)
- **500 looks:** not reachable, because of the 64 cap. Past that, the store
  becomes a folder of books: `examples/*.look.json` files are already books
  (ADR-023). They would be browsed by name in the library, with the set as the
  curated surface, like grandMA3's pool versus its executors [S1508] and Helix
  setlists [S1519]. Defer this until the cap binds.

**Save and organize.** You make a look with surprise or like this, then press
keep on the draft, or k. "save…" names it, and becomes a rename in place. In the
library, "arrange" turns the tiles into drag targets with a small menu: move to
set, rename, ↻ idle cycle, delete. WLED users force an order with numeric name
prefixes [S1505]; an explicit order makes that hack unnecessary.
`[NOT-A-MODEL]` (the WLED rationale only; the audit's case for ordering, §1.1,
stands; §9.4 replaces "arrange" with `move to key…` and drag in find)

**File.** No change: `looks` keeps its order, "which is the order the page
shows" (the `aura/book.py` docstring).

**Live.** Keys 1–9 and one tap work as at 8853368. The set never changes unless
you arrange it.

**Gives:** no file-format change, so no ADR-006 version break; you choose which
looks get keys; the deck stays the same size at any count; the fewest new
concepts.
**Takes:** only one set; order and a name filter are the only organization; a
key's look changes when you rearrange (intended, and fenced inside "arrange");
the 64 cap stays.
**Scope:** engine: `move {name, to}` and `rename {name, to}` requests that keep
the position (`aura/book.py`, `aura/looks.py`, `aura/control.py` REQUESTS).
Page: `infra/wire/protocol.ts`; `ui/deck/Looks.tsx` caps at nine and adds the
live and draft tiles; a new `LibraryPanel.tsx` on `ui/common/Panel.tsx`;
`Variety.tsx` becomes the header verbs; `LookEditor.tsx` renames instead of
save-as plus delete; `Deck.tsx` and `theme.css`. Wire: two requests, with the
state unchanged. ADR: none for the file. The new requests may need a line in
ADR-020 (inference: the look and ack messages got an amendment there).

#### Option B: banks of nine

**Model.** Looks live in **slots**, nine to a **bank**, and you flip banks like
pages. Keys 1–9 recall the slots in the bank shown, and `[` and `]` flip banks.
An empty slot shows "+". Tapping it stores the running look there, and keep
fills the first free slot, as grandMA3's Store with no number does [S1508].
Banks may have names.

```
PHONE, 5 looks                     PHONE, 50 looks
looks      ⚄ surprise ≈ like this  ‹ 3 ambient ›  ⚄ surprise ≈ like this
[dusk ][tide ][ember]              [lantern][ink   ][bloom]
[prism][warp ][  +  ]              [lagoon ][copper][depth]
master ──────●──── 70%             [fount  ][  +   ][     ]
[         BLACKOUT          ]      ● ● ● ○ ○ ○   (swipe pads to flip)

DESKTOP, 50 looks
looks  1 2 [3] 4 5 6           ⚄ surprise  ≈ like this  ?
[lantern  ][ink      ][bloom    ]
[lagoon   ][copper   ][depth    ]
[fount    ][    +    ][         ]
```

- **5 looks:** one bank; show a single "+" and hide the other empty slots.
- **50 looks:** six banks, shown as dots on a phone and numbered tabs on desktop.
- **500 looks:** not reachable; 64 looks fill about 7 banks. Past the cap,
  banks need names and a search that jumps to a slot, as with Onyx's 500 named
  banks [S1510].

**Save and organize.** You store into a slot, drag a pad onto another to swap
them, and rename in place. A slot never moves when other looks are added or
deleted.
**File.** Gaps need explicit positions. A top-level
`"banks": [{"name": "ambient", "slots": ["dusk", null, …]}]` in `aura/book.py`
leaves the look-body codec alone. That makes file version 5, and ADR-006's
clean-break rule refuses a v4 file. Because `banks` would be optional, the
amendment could instead read a v4 file as v5 without banks (inference: a policy
choice for that ADR).
**Live.** The strongest muscle memory, since a look keeps its pad. This matches
the Roland favourites [S1518], Helix footswitch banks [S1519] and Onyx swipe
banks [S1510].
**Gives:** stable positions; visible capacity ("+" answers "can I save more?"
without text); named banks match the parts of a long run.
**Takes:** the bank is a hidden mode, so key 3 means a different look in each
bank, which risks firing the wrong look mid-run (inference); the file version
changes; empty pads are noise, and filing is manual; a 3×3 grid costs about
100px more phone height than one row (inference, from 44px tiles); two
concepts, slot and look.
**Scope:** engine: `aura/book.py` (the banks section and its checks),
`aura/looks.py` (`place`, keep into a slot, state `banks`), `aura/control.py`.
Page: `protocol.ts`; a new `Banks.tsx` replaces `Looks.tsx`; the current bank
is page-local, like the fade (`ui/common/local.ts`); a browser panel holds the
filter. ADR: an ADR-006 amendment (v5) and wire lines in ADR-020.

#### Option C: starred collection

**Model.** All looks form one **collection**. A ★ marks the looks you play. The
deck shows the starred looks, with keys 1–9 on the first nine, and tags filter
the library. One **make** split button replaces the verbs: a tap is surprise,
and ▾ opens like this. Made looks you did not keep go to a short **recent**
list.

```
PHONE, 5 looks (no stars: the deck shows all)
looks                          ⚄ make ▾
[dusk][tide][ember][prism][warp]

PHONE, 50 looks                    LIBRARY PANEL
★ looks         ⚄ make ▾   all ›   [ search…                    ] ×
[dusk][tide][lantern][ink]…        (★) (warm) (slow) (drops) (+)
master ──────●──── 70%             recent: [surprise 9][like 3]…
[         BLACKOUT          ]      ★dusk   ★tide   ember   ★ink …

DESKTOP, 50 looks: the same, with the library panel in the slot.
```

- **5 looks:** no stars and no chips; stars appear only in the library.
- **50 looks:** about nine starred looks, a few tags, and search.
- **500 looks** (if the cap were lifted): search and tags carry it, as in
  Ableton [S1512] and Komplete Kontrol [S1513]. Procreate keeps a Recent set of
  eight [S1516].

**Save and organize.** Keep and save… work as in A. You star a look from the
library or with a long press, and you add tags in the editor. Which starred
look gets which key still needs an order, so C needs A's `move` too.
**File.** A per-look `star` and `tags` mean a `LOOK_KEYS` change
(`fx/codec.py:76`), which older engines refuse. Top-level `favorites` and
`tags` maps in `aura/book.py` avoid the codec change. Either way the file goes
to v5. Recent needs `made` to carry its seed, because the state sends only the
label (`aura/looks.py:198`).
**Live.** A starred look recalls as fast as in A. "Like this" moves one level
down, behind ▾, so it takes two taps.
**Gives:** it scales furthest; what is on the deck does not depend on file
order; made looks you skipped are not lost.
**Takes:** the most chrome (stars, chips and a menu), against the maintainer's "minimal
text"; tagging is upkeep nobody does mid-run, and it needs typing on a phone;
the file version changes; its payoff starts past the 64 cap.
**Scope:** engine: A's work, plus `star` and `tag` requests and their state
fields. Page: `MakeButton` (an Ark UI menu), and `LibraryPanel` with search,
chips and recent. ADR: an ADR-006 amendment (v5), and an ADR-020 line for the
`made` seed.

#### Recommendation (looks-ia): A

A book holds at most 64 looks, and the audited book has 12. A covers that whole
range with no file-format change and two concepts, the set and the library. B's
bank mode is a mid-run hazard, and C's tags pay off only past the cap. A leaves
both open (inference): named "sets" (B's banks as positional pages over A's
library) can come later if a run needs more than nine hot looks, and C's search
is A's filter box grown.

The smallest first step fixes the noun/verb confusion, page only, with no wire
or engine change:
1. Move the verbs into a looks header line, with a visible `looks` caption
   (`.cap`) at the left, and "surprise" and "like this" at the right in the
   verb style. Drop `.primary` from surprise. On desktop, the fade select moves
   into the same line. Files: `Deck.tsx`, `Variety.tsx`, `theme.css`
   (`.looks-row` 727-731, the phone stretch 756-759).
2. Keep goes onto a draft tile. While `looks.made` is set, a lit, italic tile
   `surprise 7 · keep` leads the row (`Looks.tsx`); otherwise there is no keep
   button. This ends the dashed "off" ghost and its clash with "returns here".
3. Update `web/test/ui/variety.test.tsx` and `web/test/ui/deck.test.tsx`.

After that, A in order: cap the deck at nine plus the live tile and add the
library panel; add the `move` and `rename` requests and the "arrange" mode;
optionally show each look's stored fade, master and cycle weight in the arrange
menu.

§9, §10 and [RA-27b](RA-27b-control-page-proposal.md) revise these choices:
the verbs become secondary buttons, not quiet text; keep folds into one save;
and the draft tile becomes a badge on the now line.

### 7. Nesting: options and the recommended structure (page-ia)

**Mental model.** A look is what the lights are doing: a stack of layers, each
a short run of steps with knobs, plus motions that turn knobs on their own. The
deck around it drives the aura, by switching looks and setting the room's
brightness.

```
FRAME ─ the deck, always on screen
│  looks (tap to switch) · surprise me · vary this · keep
│  brightness · blackout · fade · cues
└─ LOOK  tide •                                   revert · save…
   ├─ main knobs   shortcuts to the knobs that matter; each names its owner
   ├─ motion       ◆ breath (wave) → freq · base   ◆ bass (sound) → opacity · sparks
   └─ layers       top draws over the ones below
      ├─ sparks    pattern "sparkle"   opacity · blend · on
      ├─ echo      2 steps
      ├─ base      5 steps   ← open: holds its opacity, blend and steps
      │   └─ steps, run top to bottom: noise → kaleid → osc → fb → tint
      │       └─ knobs: freq ◆breath, shape …
      └─ wash
```

Frame controls stay in the deck, and look controls stay in the look. The one
exception is the phone's fade, which stays in the look header, because the deck
line has no room at 358px (inference).

**Rules shared by every option:**

- **One visual device per level, not one more indent.**

  | Level | Device | Heading |
  |---|---|---|
  | Frame | the deck on `--bg`: pinned on a phone, top of the side column on desktop | region "frame" |
  | Look | a full-bleed tinted band, `--surface-1` | `h2`, T1 |
  | Section (motion, layers) | a label line in the band | `h3`, T2 |
  | Layer | a row; the open one becomes a raised card (`--surface-2`, 3px amber left edge, 8px inset) | `h3` wrapping its trigger |
  | Step | a rail with a dot per step, in run order; the open step's dot is filled | `h4` wrapping its trigger |
  | Knob | spacing; a hairline only between knobs of one step | label |

- **Three type tiers** [S1525]. T1: the look name, bold, 1.15em, `--text`. T2:
  section, layer and step names, 1em, 600, `--text`. T3: knob labels, owner
  tags and readouts, `--muted`.
- **Amber means live or picked:** the current look, the picked layer's edge, the
  live mark and focus. The reset dot and switch-on move to `--text`.
- **Each signal gets a colour** (`◆`), shown on its row and on every knob it
  moves. Layers get no colour: containment carries them.
- **A one-layer look drops the layer frame.** Its steps sit right under the
  look, and the mix stays hidden at defaults, as `panelOf` does.
- **Front knobs stay in their step too.** The front copy is a shortcut, as
  Resolume shows opacity both on the strip and in Layer Properties [S1500].

| Token | Value | Check |
|---|---|---|
| `--surface-1` (look band) | `#121217` (= `--panel`) | muted text 5.46:1 |
| `--surface-2` (open layer card) | `#1a1a21` | muted 5.06:1, text 12.7:1 |
| `--edge-2` (control edge on surface-2) | `#6a6a74` | 3.24:1; `#60606a` at 8853368 is 2.78:1 there, below SC 1.4.11 [S1531] |
| `--rail` | `#2e2e38` | decorative; the headings carry the structure |
| `--sig-1…4` | `#38bdf8 #a78bfa #f472b6 #2dd4bf` | ≥6.3:1 on all three surfaces; motions take them in look order, repeating after four |

#### Option A: nested in place, one scroll (recommended)

The layout is the containment. The open layer's opacity, blend and steps sit
inside its card, and opening a row picks it. On touch the rows start closed.

- **Main knobs are shortcuts, shown twice:** leading the band, and in their
  step, as Resolume shows opacity and blend both on the strip and in Layer
  Properties [S1500]. Each names its owner in a muted tag: the step when there
  is one layer, the layer when there are more.
- **Steps start closed, and the device remembers what you open,** as the signal
  folds already do (`ui/params/ParamPanel.tsx:40`).
- **Sticky head.** The open card's head sticks as `tide › base` while you scroll
  in it [S1525].
- **Items vs actions.** Things you pick are borderless rows or filled chips.
  Verbs are quiet text buttons in the header or footer line of what they act on
  (`save…`, `+ layer`, `remove`, `surprise me`), never among the items [S1521].
- **Colour has three jobs.** Amber means *now*: the live look chip, the open
  layer's edge, focus and the top-bar state tags. Signal colours mean *motion*.
  Red means danger.
- **Motion shows both ends.** A motion row lists what it moves. A moved knob
  shows `◆ breath` and a live tick in its colour, and the "moves with" sentence
  stays for screen readers. Chromatik colours modulation by source, and lists
  each modulator's mappings [S1265].

Phone, 4 layers:

```
┌ stage ──────────────────────────────┐
├─────────────────────────────────────┤ slot scrolls
│ tide •                revert  save… │ h2 · surface-1
│ decay   ━━━━●──── 0.60   fb · base  │ main knobs
│ sides   ━━●────── 6  kaleid · base  │
│ opacity ━━━●───── 60% ◆bass sparks  │
│ motion ?                            │ h3
│ ◆ breath  wave  → freq · base     › │
│ ◆ bass    sound → opacity · sparks› │
│ layers ?                  + layer   │ h3
│   sparks  sparkle   screen 60%  (●) │ row
│   echo    2 steps          80%  (●) │
│ ╭▌base    5 steps         100%  (●)╮│ open card · sticky head
│ │ opacity ━━━━━━━━● 100%  normal ▾ ││
│ │ ┊ noise                        › ││ h4 rail
│ │ ┊ kaleid                       › ││
│ │ ● osc                          ⌄ ││
│ │ ┊   freq ?  ━━●┆━━ 1.20 ◆breath ↺││
│ │ ┊   shape   sine ▾               ││
│ │ ┊ fb                           › ││
│ │ ┊ tint                         › ││
│ │ ▲ ▼   replace…          remove   ││ footer: verbs
│ ╰──────────────────────────────────╯│
│   wash    wash            100%  (●) │
╞═════════════════════════════════════╡ deck · --bg · pinned
│ looks         surprise me  vary this│
│ [surprise 7 · keep] [dusk] [tide] … │ chips; draft first
│ brightness ━━━━●── − 70% +  max 80% │
│ cues off   [kick] [drop]            │
│ [            BLACKOUT             ] │
└─────────────────────────────────────┘
```

Phone, 1 layer:

```
│ tide •          revert  fade ▾  save… │
│ decay  ━━━━●──── 0.60            fb  │ owner = step
│ sides  ━━●────── 6           kaleid  │
│ motion ?                             │
│ ◆ breath  wave → freq · osc        › │
│ base · 5 steps              + layer  │ h3, no card
│ ┊ noise                           ›  │
│ ● osc                             ⌄  │
│ ┊   freq ?  ━━●┆━━ 1.20  ◆breath  ↺ │
│ ┊ fb                              ›  │
╞══════════════════════════════════════╡ deck as above
```

Desktop, 4 layers (side column, stage to its left):

```
top bar: tide • · brightness 70%        SHUFFLE  ok  layout  help
─ deck · --bg ────────────────────────────────────────────────
[BLACKOUT]   brightness ━━━━●── − 70% +
looks  fade: as saved ▾                 surprise me  vary this
[surprise 7·keep] [dusk] [tide] [ember] [prism]
cues on   [kick] [drop]
─ look band · surface-1 ──────────────────────────────────────
tide •                                        revert  save…
decay ━━●── 0.60 fb·base     sides ━●── 6 kaleid·base
motion ?  ◆ breath wave → freq·base ›   ◆ bass sound → opacity·sparks ›
layers ?                                            + layer
  sparks  sparkle                          screen 60%  (●)
╭▌base    5 steps                                100% (●) ╮
│ opacity ━━━━━━● 100%                     blend normal ▾ │
│ ● osc ⌄   freq ? ━━●┆━ 1.20 ◆breath ↺   shape sine ▾    │
│ ┊ noise ›  ┊ kaleid ›  ┊ fb ›  ┊ tint ›                 │
╰─────────────────────────────────────────────────────────╯
  wash    wash                                   100% (●)
```

Desktop, 1 layer:

```
├─ look band ──────────────────────────────────────────────────────┤
│ tide •                                           revert  save…   │
│ decay ━━●── 0.60  fb         sides ━●── 6  kaleid                │
│ motion ?   ◆ breath  wave → freq · osc  ›                        │
│ base · 5 steps                                      + layer      │
│ ┊ noise ›  ┊ kaleid ›  ● osc ⌄  ┊ fb ›  ┊ tint ›                 │
│     freq ?  ━━●┆━━ 1.20  ◆breath  ↺      shape  sine ▾           │
```

- **Gives:** the layout is the containment, with no modes and no new kinds of
  selection. A one-layer look gets shorter. Phone and desktop share one layout,
  like Ableton's brackets [S1512] and Blender's panels [S1528].
- **Takes:** about 8px more inset on a phone. Opening one layer pushes the rows
  under it down. With many layers the list scrolls: 16 closed rows are about
  700px at 44px each (inference).
- **Changes:** the slot renders only `LookPanel`, which holds the front knobs,
  new `SignalRow`s (from a new `routesFrom`) and `LayerList`. `LayerRow`'s body
  renders `LayerKnobs(layer)`. Step folds become a `StepRail` (a `::before`
  rail and an `h4`). `panelOf` keeps the front knobs in their step.
  `ParamField`'s `moved` sentence becomes a `◆` mark.

#### Option B: stack plus inspector (master–detail)

```
 stage
────────────────────────────────────
  tide •                 revert save…  root row = the look
  ├ sparks  sparkle  scr 60% ◆  (●)
  ├ echo    2 steps      80%    (●)
  ├▌base    5 steps     100%    (●)   picked
  └ wash    wash        100%    (●)  + layer
════════════════════════════════════  inspector, surface-1
  tide › base              reset  ⋯   sticky
  opacity ━━━━━━● 100%   normal ▾
  noise  kaleid [osc]  fb  tint        step tabs
  freq  ━━●┆━━ 1.20   ◆ breath ±0.2
  shape sine ▾
 deck
```

Pick the root row to inspect the look: its front knobs, its signals with their
targets, and save. On desktop, a stack column (~200px) sits under the deck,
beside the inspector:

```
┌── stage ──┬── deck ─────────────────────────┐
│           ├─ stack ──────┬─ inspector ──────┤
│           │ tide         │ tide › base      │
│           │ ├ sparks 60% │ opacity ━━● ▾    │
│           │ ├ echo   80% │ noise [osc] fb … │
│           │ ├▌base  100% │ freq ━●┆━ ◆      │
│           │ └ wash  100% │                  │
└───────────┴──────────────┴──────────────────┘
```

With one layer there is no stack: the inspector shows the look, with the step
tabs under its front knobs.

- **Gives:** one thing in focus; it scales to 16 layers; tree lines say "child of
  the look". It matches Figma [S1527], Resolume [S1500], TouchDesigner [S1529]
  and the HIG inspector [S1522].
- **Takes:** the front knobs, the ones played live, leave the screen while a
  layer is picked; tabs hide the other steps; a tap is needed to move between
  look and layer; on a phone, list and inspector compete with the stage and the
  deck.
- **Changes:** a new `StackTree` (a radio list, no accordion) and an `Inspector`
  (a body per kind: look, layer, signal); selection gains `look` and
  `signal:<id>`; steps use Ark `Tabs`; desktop nests a `Splitter` in `.side`.

#### Option C: front face plus structure sheet (play / edit)

```
 stage
────────────────────────────────────
  tide •                      edit ›
  decay   ━━━━●──── 0.60      base
  sides   ━━●────── 6         base
  opacity ━━━●───── 60% ◆     sparks
  ◆ breath ∿∿∿     ◆ bass ▮▮▯         live meters
 deck
```

`edit ›` swaps the slot for drill-down pages, as `+ layer` swaps it at
8853368:

```
‹ tide    layers   + layer  │ ‹ layers  base     ⋯ │ ‹ base  osc
sparks  scr 60% (●)  ›      │ opacity ━━━● normal▾ │ freq ━━●┆━ 1.20
echo        80% (●)  ›      │ noise ›  kaleid ›    │ ◆ breath ±0.2
base       100% (●)  ›      │ osc ›  fb ›  tint ›  │ shape sine ▾
wash       100% (●)  ›      │                      │
```

On desktop the pages open in a column beside the face. With one layer,
`edit ›` opens on the steps.

- **Gives:** the smallest live surface, like Ableton's macro bank [S1512], and
  unbounded edit depth.
- **Takes:** a mode to learn; two or three taps to a step knob that is not in
  front; three levels deep, past NN/g's two [S1524]; the most new code.
- **Changes:** a new `FrontFace`, and a `StructureSheet` (a `Panel` with a back
  stack: `[] | [layer] | [layer, step]`). `LayerList` and `LayerKnobs` are
  reused as page bodies.

#### Recommendation (page-ia): A

A fixes problems 1–8 of §1.2 with the fewest new ideas, keeps one scroll on
phone and desktop, and makes a one-layer look simpler than it is at 8853368.
From B it takes only the sticky `tide › base` header on the open card. Revisit
B if looks often pass about 6 layers, and C if the main knobs get lost below
the fold in live use.

**Against looks-ia (§6).** *Same:* verbs in a `looks` header line with
`.primary` dropped; a draft chip with `keep` leads the row, so there is no dead
keep button; two disclosure levels at most; set and library come later; no
arranging on the deck; the phone's fade stays in the look header. *Different:*
the words "surprise me" and "vary this" (§8); no ⚄ and ≈ glyphs, which needed a
font check; no "?" in the deck header on a phone, since off verbs explain
themselves when pressed and the marks go in the help sheet; looks are filled,
borderless chips; "save…" also covers an edited saved look, which `keep` does at
8853368 (`keepReason`, `domain/aura/looks.ts:75`).

**page-ia's phases.** Each phase is one branch passing `just ready`; phases 1–5
touch only the page. [RA-27b](RA-27b-control-page-proposal.md) §7 folds them
into the final proposal's three phases.
1. **Deck, items vs actions:** verbs go in the `looks` header line, with
   `.primary` dropped; saved looks become borderless chips; a draft chip with
   keep; the deck and top-bar words (surprise me, vary this, brightness, max,
   fade labels, cues on/off, SHUFFLE). Touches `ui/deck/{Deck,Variety,Looks,
   Master,Triggers,Cues}.tsx`, `domain/aura/{looks,master}.ts`,
   `ui/status/TopBar.tsx`, `ui/theme.css`, and
   `web/test/ui/{deck,variety,arm}.test.tsx`.
2. **Containment:** the slot renders only `LookPanel`; `LayerRow`'s body holds
   that layer's mix and steps; a one-layer look shows its steps directly;
   `panelOf` keeps main knobs in their step; `contextsOf` always names the
   owner; headings h2/h3/h4. Touches `app/App.tsx`, `ui/deck/LookPanel.tsx`,
   `ui/stack/LayerList.tsx`, `ui/params/ParamPanel.tsx`,
   `domain/stack/stack.ts`, `ui/stack/selection.ts`,
   `web/test/domain/stack.test.ts`, and `web/test/ui/{layers,params}.test.tsx`.
3. **Visual system:** the tokens, the card, the step rail and a sticky head;
   the type tiers; amber kept for what is live now; ↺ for reset; switch-on and
   segment-on in `--text`; the shared accordion rail (`theme.css:1018`) goes.
   Touches `theme.css`, `ui/params/ParamField.tsx`, `ParamPanel.tsx` (a new
   `StepRail`) and `LayerList.tsx`.
4. **Motion both ways:** a motion row shows its kind and targets (a new
   `routesFrom`), and a target opens its step; a colour per motion, with a `◆`
   mark and a coloured live tick. Touches `stack.ts`, `ParamPanel.tsx` (a new
   `SignalRow`), `ParamField.tsx`, `ui/params/controls/number.tsx`, `theme.css`
   and tests.
5. **The "? note" and the remaining page words:** a `Note` with a store that
   keeps one open, the help sheet and the glossary; remove the knob-help
   overlay and the `title`-only reasons; rename the shelves, `5 steps`, the
   "params" heading, the "more ▸" variants, and "colour" for stop. Touches
   `ui/common/AboutButton.tsx`, `ParamField.tsx`, `Variety.tsx`,
   `LayerList.tsx`, `TopBar.tsx`, `ui/status/ShortcutHelp.tsx`,
   `ui/stack/AddLayer.tsx`, `domain/stack/catalog.ts`,
   `ui/params/controls/palette.tsx`, a new strings file, and `theme.css`.
6. **Engine and docs words:** pattern titles (geq, sdf3d); the argument labels
   that still default (Freq, Gain, Attack…); the blend labels max and min; the
   hold refusal becomes "A cue is playing Y. Save after it ends.", mirrored in
   `holdReason` (`domain/aura/looks.ts:70`). Touches `src/pewpew/patterns`,
   the `label=` in `fx/ops/*.py`, the blend label source, the `aura/`
   refusals, `docs/authoring.md`, `docs/reference/catalog.md`, the engine tests
   that assert these strings, and `CHANGELOG.md`.

### 8. Words: glossary, copy rules and the "? note" (page-ia)

#### Glossary

The UI word is the only word, in labels, notes, aria names and docs. No wire
field or knob address changes. The **party test** asks whether a friend at a
party would get the word unaided (✓ yes, ~ maybe, ✗ no). It rests on NN/g's
"speak the users' language" [S1526]. "page" in the last column means a label
change in `web/src`.

| Code term | On the page at 8853368 | Test | UI word | Learn-more (≤12 words) | Touches |
|---|---|---|---|---|---|
| aura | (renamed 2026-11-06) | — | aura, as in the chip's "aura health" and the hidden h1 "pewpew aura control" | What runs the lights: it plays looks and takes your requests | page, engine |
| frame | (renamed 2026-11-06) | — | frame, the deck region's aria name; never a heading | — | page |
| look | look name | ✓ | look | Everything the lights are doing, saved under one name | — |
| book | — | — | looks | Your saved looks; tap one to switch to it | page |
| recall | titles | ✗ | switch to | — | page |
| surprise | surprise | ~ | surprise me | A brand-new look, made for this room | page, authoring.md |
| vary | like this | ✗ | vary this | A new look close to the one playing | page, authoring.md |
| made look | (top bar and look heading only) | — | its name in italics `· keep` | Not saved yet: keep saves it under this name | page |
| keep | keep | ~ | keep | Saves the made look under its name; rename with save… | — |
| changed | dot | ~ | • (unsaved only) | Changed since saved | page |
| master | master | ~ | brightness | Whole-room brightness, on top of every layer | page |
| cap | cap 80% | ✗ | max 80% | Highest brightness allowed in this run, set at launch | page |
| fade | fade: saved / cut | ~ | fade: as saved / instant / 2 s | How long switching looks takes | page |
| idle cycle | IDLE CYCLE, ↻ in idle cycle | ~ | shuffle, SHUFFLE, ↻ | When nobody touches anything, ↻ looks play in turn | page, authoring.md |
| idle cycle `idle` | (shown as text only) | ✓ | starts: right away / after 5 min untouched | When shuffle starts, and how long a touch pauses it | page |
| idle cycle `each` (dwell) | (shown as text only) | ✓ | each look: 2 min; `every 2 min` | How long each look plays before the next | page |
| trigger, cue, arm | triggers: ARMED, cues (arm first) | ✗ | cues on / off; cues | Plays a look for a few seconds, then comes back | page; engine refusals |
| front | (no word) | ~ | main knobs (no visible heading) | The few knobs this look is meant to be played with | page |
| signal | motion · hue | ~ | modulator, under the heading modulators | A modulator keeps a knob moving: a wave, the beat, the music | page |
| lfo, walk, band, beat, env, smooth | lfo, walk, band, env, smooth | ✗ | LFO, random, audio follower, beat, envelope, smooth | one line each in the help sheet (§12.2) | page, engine `label=` |
| knob signal (macro) | value · macro | ✗ | macro; its row reads `name → 3 knobs` | One knob you turn that moves several others at once | page, engine `label=` |
| route, depth | moves with hue, ±180 | ✓ | `modulated by ‘name’ ±0.2`; + or − for a one-way kind | How far a modulator moves this knob; saving keeps your setting | page |
| layer | layers | ✓ | layer | One picture; higher layers draw over lower ones | — |
| opacity | opacity | ~ | opacity | How much of this layer shows; 0 hides it | — |
| blend | blend | ~ | blend (max → lighter, min → darker) | How this layer mixes with the layers below | engine labels |
| pattern | pattern | ✓ | pattern | A ready-made animation: pick one, then tune its knobs | — |
| pattern names | geq, sdf3d | ✗ | sound bars, ring | (the card line explains) | engine titles, catalog.md |
| program | custom · 3 steps | ✗ | `5 steps` | A layer built from steps: one draws, the rest change it | page |
| node | flies · particles | ~ | step | One step of a layer: it draws, bends or colours | — |
| op shelves | sources / space / color / combine two fields | ✗ | draw / warp / colour / mix two | e.g. warp: Bends the picture: mirror, twist, kaleidoscope | page |
| ops | effects (advanced) | ~ | build your own | Make a layer from steps instead of a ready pattern | page |
| param | params | ✗ | knobs (the heading is the owner's name) | — | page |
| arg labels | Freq, Gain, Attack | ✗ | Stripes, Boost, Rise | (existing help) | engine `label=` |
| reset | dot | ✗ | ↺ | Back to default (Backspace) | page |
| palette | palette | ~ | palette | The colours a layer paints with, as a gradient | — |
| palette stop | stop 1 of 3, add stop | ✗ | colour 1 of 3, add colour | One colour of the gradient, at a point along it | page |
| unattended run | — | — | an unattended run (docs and `run --help` only) | — | docs |

The aura and unattended-run rows were named on 2026-11-06, after this study
(RA-29, `research/topics/RA-29-naming-the-aura.md`). "Frame" is RA-27b's own
word for that region (§3), used for it from the same date. The aura is the
running engine, `pewpew.aura`: it plays looks on the lights and takes
operator requests. The frame is the deck's region (`aria-label="frame"`,
`web/src/deck/Deck.tsx:149`): the saved looks, the make actions, the cues,
brightness and blackout. An unattended run is `run --unattended`: it holds a
sleep assertion, arms the loop watchdog and leaves a failing layer out of
the mix (`src/pewpew/__main__.py:191-193`).

The four modulator rows follow the maintainer's decision of 2026-11-06 and §12. They
read motion; wave, wander, sound, beat, swell, glide; `→ 3 knobs`; and
`◆ name ±0.2` before it.

These stay as they are, or off the page: blackout/restore (✓), the on switch
(✓), made-look names (✓), and dashed "returns here after a cue" (~). Seed,
sweet, book and node ids don't appear on the page. Health, layout, blink and DDP
belong to the maintainer's operator panels, so their jargon stays. Where the two page-ia
notes differ, the table follows the later proposal: a program reads `5 steps`,
not `particles +2`, because the open card lists the steps; and a macro's label
is its name with `→ 3 knobs`, not just the signal's name. The language study's
"Sync → Speed" row is dropped, because osc's `sync` already reads "Drift"
(§1.3).

Word choices and their evidence:
- **Keep the words people already search for.** Resolume uses layer, opacity
  and blend mode [S1500]. Pixelblaze [S552] and Chromatik [S1265] say
  pattern.
- **"brightness", not "master".** Consoles say grandmaster [S1511], and each
  Resolume layer has its own "Master" fader [S1500], so "master" is ambiguous
  (inference). On a phone the top bar can drop the word and keep "60%".
- **"shuffle", not "idle cycle",** since music players made it familiar
  (inference). Pixelblaze's sequencer offers "Shuffle All" and "Playlist"
  [S552], and WLED chains presets into playlists [S554]. `[NOT-A-MODEL]`
  applies to the WLED evidence only; the word now rests on Spotify's shuffle
  [S1556] (§9.4).
- **Keep "palette".** It clashes on consoles, where a palette is a stored
  reference [S1511], but WLED uses it as pewpew does, for a gradient [S1504].
  `[NOT-A-MODEL]` (WLED was the only evidence for keeping the word; it must pass
  the in-place word test, §9.4)
- **Engine strings need an engine and docs change.** These are the hold
  refusals ("trigger X holds look 'Y'; keep once…", mirrored in
  `domain/aura/looks.ts:70`), pattern titles, argument labels and blend labels.
  The suggested hold refusal is "A cue is playing Y. Save after it ends."
- **Authors name a signal for what it does** ("drift"), not for the knob it
  moves. At 8853368 a hue knob reads "moves with hue".

Comparable tools: Resolume's layers stack upward, each with a blend mode and
opacity, and its Dashboard holds dials for your most-used parameters, matching
`front` [S1500]. Ableton's Macro Controls each drive "any number of parameters",
Macro Variations store their states, and "Rand" randomises them, matching
macro, look and surprise [S1512]. WLED presets save segments and brightness
[S554], and its effect parameters include Speed and Intensity [S1504].
Chromatik's modulators drive a "Parameter Mapping" with a "Range", matching
signal, route and depth [S1265].

#### Copy rules

1. **Actions are verbs; things are nouns.** Buttons start with a verb ("surprise
   me", "vary this", "keep", "save…", "remove"). Look, layer and pattern names
   never do, so the words back up the visual split between actions and items.
   "…" means the button opens something.
2. **One word per thing, one sign per meaning:** • unsaved, ↺ reset, ↻ in
   shuffle, ± how far a modulator moves a knob (§12.3), ? explain, amber now.
   Say cue, not trigger or arm; brightness, not master; switch to, not recall;
   modulator, not motion or signal. WCAG 2.2 SC 3.2.4 asks
   for one name per function [S1531][NEEDS-VERIFICATION] (the page was not
   fetched).
3. **Short.** Labels are 1–2 words, in lower case, as the CSS renders them.
   Notes are fragments of 12 words or fewer, with no full stop. A reason says
   the fix ("switch to a look first").
4. **Headings name the owner.** A knob outside its step names its owner ("swirl
   · ink"), which `contextsOf` already does once there are two or more layers.
5. **Talk about the lights and the room.** Outside the operator panels, never
   say render, engine, node or param, and show no builder code. Chains,
   addresses, flags and argument names stay in the docs. The "more ▸" variants
   get plain names or move under "build your own".
6. **When text appears:** labels always; learn-more on "?"; a reason when its
   off control is pressed; errors by their control until fixed; room-wide
   failures in the status bar. Never on hover alone, and never in a tour.

#### Learning more: one pattern

| Pattern | Verdict |
|---|---|
| Tooltip (hover/focus) | No. It doesn't work on touch, and must never hold task-critical information [S1524]. The APG tooltip pattern is still "work in progress" [S1530]. |
| `title` attribute | Duplicate text only. It is outside SC 1.4.13 because the browser controls it [S1531], but phones never show it [S1524]. |
| Focus overlay (knob help at 8853368) | Remove. It covers the next knob and has no Escape, which fails SC 1.4.13's "dismissible" on a strict reading [S1531] (inference from the CSS). |
| Toggletip (click "?") | Yes. It behaves the same on touch and with a mouse [S1532]. |
| Popover (Ark, HTML `popover`) | Not needed: it would cover controls while the lights run (inference). The Popover API is Baseline 2025 [S1533]. |
| Coach marks / first-run tour | No. Users dismiss them and forget them within about 20 s [S1524]. |
| Glossary sheet | Yes, as the second way in, using the same strings. |

**The "? note"** is an inline toggletip built as an APG disclosure [S1530].

- **Where it goes:** a quiet "?" right after a term that fails the party test,
  and nowhere else, because help that adds nothing should be skipped [S1524].
  That means the concept words (modulators, layers, blend, cues, the shuffle
  tag, max) and each knob with engine `help`.
- **What opens:** one line under that row, in the page flow, never over
  controls. It says what the thing is, and when the control is off, why and the
  fix ("keep is off: firefly-ink is already saved"). Pressing an off control
  opens its note, as Variety does at 8853368. Reasons move out of `title`.
- **Behaviour:** one note open page-wide, through a small shared store. A second
  tap or Esc closes it, focus stays on the "?", and the "?" carries
  `aria-expanded` and `aria-controls` [S1530].
- **On knobs,** a "?" by the label replaces the focus overlay
  (`ui/theme.css:927-943`), and only knobs that have help get one.
- **The second way in:** the top-bar "?" becomes **help**, a sheet (the
  `ShortcutHelp` dialog) with the glossary, plus the shortcuts on a keyboard. So
  "?" always means "explain". The notes and the sheet share one strings file.
  That keeps help to two levels (label, then note or sheet); deeper than that
  "typically [has] low usability" [S1524].
- **It replaces** the focus-only knob-help overlay, the `title`-only reasons
  (phones never show them [S1524]), the top-bar tag notes, and `AboutButton`.
- **Not used:** hover tooltips, floating popovers (they cover live controls,
  inference), and first-run tours [S1524].

`AboutButton` at 8853368 is click-only, so it is outside SC 1.4.13 [S1531]. Its
content is inline, it has a 24/44px target through `--target`, and it is named.
The changes: `aria-expanded` and `aria-controls` instead of `aria-pressed`,
since it shows and hides content [S1530] (inference); Esc to close; one note
open page-wide; and only the pressed item's line and reason, not the Variety
note's three general lines, which push master and blackout down on a phone
(phone screenshot, "?" open).

**WCAG 2.2 scope.** Kept:
- 1.3.1: headings h2, h3 and h4 wrap the accordion triggers [S1530][S1531].
- 1.4.11: control edges and states keep 3:1 on each surface (§7 token table)
  [S1531]. 1.4.3 (text contrast) is kept too; its Understanding page was not
  read.
- 1.4.13: notes open only on click and stay in the page flow [S1531].
- 2.4.7: focus is visible; `:focus-visible` already provides it [S1531].
- 2.5.8: targets are at least 24px, and 44px on touch, which `--target` meets
  [S1374].
- 3.2.4: one word for each function [S1531][NEEDS-VERIFICATION].
- 3.3.2: a visible label, and units, on every control [S1531].
- 4.1.2: name and state are exposed, including on each "?" [S1531].

Skipped: a formal audit or VPAT, AAA, screen-reader narration of live readouts,
localisation, a docs site, and links out of the page. Op docs stay in
`docs/reference/catalog.md`.

### 9. Design-led patterns (Spotify, Linear, Figma, Vercel/Geist, Superhuman)

The study ran on 2026-11-05 at the maintainer's direction (top of this doc): one note per
product, then a patterns note checked against §6, §7–§8 and §10. This section
rewrites them. Each transfer to pewpew is an inference. **CONFIRM** keeps an
earlier call, **REFINE** changes it, and **REPLACE** drops it.
[RA-27b](RA-27b-control-page-proposal.md) turns the result into the final
proposal, and makes three calls of its own, noted below.

These are products, read as UX references, not as code to build on. The one
code source is Figma's Simple Design System (MIT, pinned [S1577]). Claims the
notes drew from product knowledge, with no source, are left out.

#### 9.1 What each product shows

- **Spotify.**
  - Encore has three button tiers under one size scheme [S1551]. Play is the
    one filled accent: black text on green at 10.9:1, in sentence case
    [S1550].
  - One Plus saves at once, and a second tap picks where it goes [S1559].
  - Generated content stays apart until kept. Smart Shuffle marks its picks
    with ✨ and keeps them out of the playlist until you save one [S1555]. AI
    Playlist saves nothing until "Create" [S1557].
  - The generators sit behind one "+ Create" button, not among the items
    [S1558].
  - Pins sit at the top of the library, up to 20 since July 2026 (a news
    report) [S1560].
  - Library and Now Playing are separate regions [S1554].
  - The shuffle icon cycles through off, Shuffle and Smart Shuffle [S1556].
  - ? or ⌘/ opens a shortcuts dialog that works from the keyboard and with
    screen readers [S1552].
  - Names are tested in a real sentence with users [S1553].
- **Linear.**
  - The 2026 refresh: "Don't compete for attention you haven't earned"
    [S1561], and header actions in the same slots on every object type
    [S1562].
  - The "inverted L" chrome "controls the content in the main view", with side
    panels for properties [S1563].
  - Plain words: "Projects should be called projects" [S1564].
  - Cmd+K and `/` reach any page or action [S1565]. Menus show each action's
    shortcut [S1566], and `?` opens the shortcut help [S1567].
  - Objects are starred [S1568], and the sidebar is reordered by drag
    [S1569].
  - A parent lists its sub-issues inside it, with chosen properties on each
    row [S1570].
  - The Edit button went, so you edit in place [S1571].
- **Figma (UI3).**
  - UI that showed only on hover was rejected as "too unstable". UI3 stripped
    features "until they were missed", and moving controls "disrupted muscle
    memory too much" [S1572].
  - Floating panels were reverted ("Speed is a feature"). A label-free design
    was dropped for accessibility, and blend mode moved from behind an icon to
    an inline dropdown [S1573].
  - The right sidebar follows the selection, and shows file-level controls
    with nothing selected [S1527]. In Minimize UI it opens on selection and
    folds on deselect [S1576].
  - An instance shows one set of consolidated controls. "Simplified
    instances", which hid inner layers, are deprecated from 23 March 2026
    [S1574].
  - A changed instance keeps Reset and "Push changes to main component" beside
    its name [S1575].
  - The toolbar holds the verbs, and the canvas holds the things [S1578].
  - The SDS Button has `primary | neutral | subtle`, and a separate
    `ButtonDanger` is "Only used for destructive actions"
    [S1577:src/ui/primitives/Button/Button.tsx].
- **Vercel Geist.**
  - One Button with a variant prop: "Disable a button only when the action is
    impossible right now" [S1579].
  - A split button holds one clear default and 1–4 close variants [S1580].
  - Menus put destructive items last, after a divider [S1581]. A context menu
    "must never be the only entry point" [S1582].
  - The command menu shows recent items before you type [S1583].
  - An undo toast reads "{Noun} {past-participle}" and stays 5–10 s [S1585].
  - Badges are static labels [S1586]. An entity row allows at most two
    controls, and the rest go under ⋯ [S1587].
  - Tooltips come last, since "Touch users can't reach a hover-revealed
    control" [S1588].
  - "Three CTAs is a smell" [S1589].
  - The guidelines: inline help first, "as few unique terms as possible", and
    undo with a safe window for destructive actions [S1590].
- **Superhuman.**
  - The command palette is "the one place where users can find every
    command". It teaches each shortcut, maps synonyms, and the buttons stay
    [S1591].
  - It aims for "latency less than 50ms" [S1592].
  - Generated drafts get a slot of their own, three per conversation,
    precomputed [S1593].
  - Reading hides the inbox, and every screen asks "What can I remove"
    [S1594].
  - "Checklists, tooltips, and timed nudges… yielded zero impact", while
    teaching right after an action worked [S1595].
  - Z undoes the last action within 10 s [S1596][NEEDS-VERIFICATION].

#### 9.2 Principles (the study's synthesis)

1. One accent, and one primary per screen, shown only while it can act
   [S1561][S1550][S1577][S1579].
2. Things are tiles and actions are buttons, never the same component
   [S1568][S1578][S1587].
3. A made look is a labelled draft until saved [S1555][S1557][S1593].
4. The frame is fixed, and the selection sets what the panel shows
   [S1554][S1563][S1527].
5. Every level has the same header slots, and the header holds the path
   [S1562].
6. Undo instead of asking [S1596][NEEDS-VERIFICATION][S1585].
7. One word per thing, labels always on, help inline before any tooltip
   [S1564][S1573][S1590].
8. Respond on press, in under 50 ms [S1592].

#### 9.3 Patterns by problem

**(a) Saved looks vs actions that make a look.**
- **A make group.** Surprise me and vary this become two secondary buttons on
  their own row, as Spotify keeps its generators behind "+ Create" [S1558] and
  Figma keeps verbs in the toolbar [S1578].
- **A now line.** The made look shows there with save beside it, and it gets
  no key. Smart Shuffle [S1555] and Superhuman's drafts [S1593] both keep
  unsaved picks apart.
- **A changed saved look is an instance with overrides.** It reads
  `● changed · tide` with `save ▾`, as Figma keeps Reset and Push beside the
  name [S1575].
- **Discard means undo**: `undo` returns to the previous look
  [S1596][NEEDS-VERIFICATION][S1585].
- Against the earlier studies:
  - CONFIRM: the verbs leave the looks row, and surprise loses `.primary`
    (§6).
  - REPLACE: the draft tile with a keep segment that led the row (§6, §7). The
    row holds only saved looks.
  - REFINE: the italic mark becomes the word `draft` plus ✦ (WCAG 1.4.1).
    There is no dashed edge, because dashes already carry three meanings
    (§1.4).
  - Not adopted: Superhuman's three drafts, and a `Surprise ▾` split, which
    would put vary this two taps away.

**(b) From 5 to 64 looks.**
- **Up to nine looks on keys, in an order you choose.** Spotify pins at the
  top of the library [S1560]. Linear stars objects [S1568] and reorders its
  sidebar by drag [S1569].
- **Past nine, one find surface.** It opens on ⌘K, `/` or a phone button, and
  lists recents, keyed looks, all looks and actions [S1565][S1591][S1583].
- **Library rows are entities,** with at most two controls and the rest under
  ⋯. Long-press opens that menu too, never as the only way in
  [S1587][S1582].
- Against the earlier studies:
  - CONFIRM: looks-ia option A (a set plus the library, with no file-format
    change) and its `move` and `rename` requests (§6).
  - REFINE: the study picked the set with ☆ or "pin to key…". RA-27b keeps
    file order instead: a look gets a key by `move to key…` or a drag in find,
    so the file stays at version 4.
  - REPLACE: "filter above 12 looks", which came from WLED, becomes find,
    there from the first look. Option C's tags go.

**(c) Nesting: frame, look, layer, step, knob.**
- **A fixed frame.** Brightness, fade, blackout, cues and the now line
  stay in the deck, as Linear's chrome frames the main view [S1563] and
  Spotify keeps Now Playing apart from the library [S1554].
- **A layers list plus an inspector.** With nothing selected, Figma's panel
  shows file-level controls; with a layer selected, that layer [S1527].
  Linear lists sub-issues inside the parent [S1570]. The look is the top row:
  picking it shows the main knobs and motion, and picking a layer shows its mix
  and steps.
- **The inside stays reachable,** since Figma is retiring the instances that
  hid inner layers [S1574]. So main knobs also stay in their step.
- **The path is the header,** with the same slots at every level [S1562].
- **A phone shows one thing at a time,** as Superhuman hides the inbox while
  you read [S1594]. A picked layer replaces the list, and `‹ tide` goes back.
- Against the earlier studies:
  - REPLACE: page-ia option A (nested in place) gives way to its option B
    (list plus inspector). Page-ia rejected B because the main knobs leave the
    screen while a layer is picked. Figma's empty-selection panel answers that
    on desktop, where the main knobs stay in view; on a phone they are one tap
    back. The "revisit past 6 layers" rule is dropped.
  - CONFIRM (§7): one visual device per level, three type tiers, motion at
    both ends, steps that start closed, and no list for a one-layer look.
  - REFINE: the sticky `tide › base` head becomes the path header. The study
    had each crumb switch to a sibling. RA-27b keeps that for the layer crumb
    only, since the look crumb must not switch looks. How Geist's breadcrumb
    menu behaves was not found [S1584].

**(d) Save, action tiers and the shared buttons.**
- **One Button with three tiers and a separate danger style,** as in Encore
  [S1551], Figma's SDS [S1577] and Geist [S1579].
- **Save is the primary, shown only when there is something to save.** Linear
  edits in place, with no Edit step [S1571], so save only names the result;
  and "Three CTAs is a smell" [S1589].
- **One tap saves; options come after,** as Spotify's Plus does [S1559].
  `save` stores a draft under its made name or updates the changed look. Its
  `▾` holds save as new…, as in Geist's split button [S1580].
- **Undo instead of a second press** [S1585][S1590]. Delete, remove, revert
  and reset all act at once. Blackout keeps two presses, because the room sees
  it before any undo (inference).
- **Disable only when impossible, and say why** [S1579], inline, since touch
  has no hover [S1588].
- Against the earlier studies:
  - CONFIRM: the actions study's `Button` (`variant`, `tone="danger"`, `busy`,
    `reason`), `IconButton`, `ToggleButton`, `Chip`, `Disclosure`, and its
    colour grammar (§10).
  - REPLACE: surprise as the deck primary (§10) becomes secondary. The two
    verbs `keep` and `save…` become one, `save` [S1590].
  - REFINE: save moves from the look header to the now line, a single fixed
    slot [S1562]. RA-27b does this in phase 2. `confirm` becomes act-then-undo
    everywhere but blackout, and undo needs an engine request.

**(e) Naming and learning more.**
- **Plain nouns, one each, with no synonyms** [S1564][S1590].
- **Labels are always on and match the accessible name** [S1573].
- **Help comes in tiers: the label, then a `?` note, then the help sheet.**
  Inline help comes first and tooltips last [S1590][S1588]. The `?` key opens
  one sheet of words and keys, like Spotify's [S1552] and Linear's [S1567].
  Menus show each action's key, which teaches it [S1566].
- **Teach in the moment, not with a tour** [S1595]: the first save toast says
  which key the look got, once.
- **Test the names in place** [S1553]. Find maps synonyms such as preset and
  scene onto pewpew's words [S1591].
- Against the earlier studies:
  - CONFIRM (§8): the "? note" and help sheet, labels always on, no hover-only
    text, no tours, one sign per meaning, and the party test.
  - REFINE: add one-time hints in toasts. Before the engine strings change
    (§7, page-ia phase 6), test "motion", "main knobs", "brightness" and "step"
    with about five people on a phone [S1553].

#### 9.4 The WLED-tagged items, resolved

WLED is not a model. Each item this doc tagged `[NOT-A-MODEL]` (formerly
`[SUPERSEDED-PENDING]`) is settled here. The WLED facts in §2 stay recorded as
facts.

| Item | Where | Verdict | Now rests on |
|---|---|---|---|
| Verbs apart from items, in the list's chrome | §2 pattern 1, §6 | CONFIRM | the consoles [S1508][S1510], the HIG [S1521], Spotify [S1558], Figma [S1578], Geist [S1587] |
| A small set of looks first, then the library | §2 pattern 2 | REFINE | the first nine with keys and full names, not 2-character circles; Spotify [S1560], Linear [S1568] |
| A search box only past about 12 looks | §2 pattern 3, §6 A | REPLACE | find, from the first look [S1565][S1591][S1583] |
| An arrange mode, against numeric name prefixes | §6 A | REPLACE | `move to key…` and drag in find [S1569]; the audit's case for an order (§1.1) stands |
| The word "shuffle" | §8 | CONFIRM | Spotify [S1556] |
| The word "palette" | §8 | open | the in-place word test [S1553] |

Also dropped: "+ Preset / + Playlist" as evidence for separating verbs; name
sorting; row edit pencils; and "use current state / overwrite with state",
which `save ▾` replaces [S1575].

Kept, since none of it came from WLED: the HIG on selection controls, NN/g on
disclosure, the WCAG choices, and the colour grammar.

#### 9.5 Not found

- A public Encore button spec with sizes or states [S1551]. The live
  spotify.design pages return 404, so S1550, S1552 and S1553 were read from
  Wayback captures.
- A public Linear button spec, Linear's empty-state guidance, and its peek
  doc (404).
- How Geist's breadcrumb menu behaves [S1584].
- Superhuman's help centre (403; search text only [S1596]) and any public
  Superhuman design system.
- Figma's Config 2024 UI3 talk, and Figma docs on layer-row indent and
  selection colours.

### 10. Action hierarchy and the shared button system (actions)

§1.4 gives the button inventory at 8853368 and where it breaks.

**Conventions:**

- **Material 3:** filled buttons have "the most visual impact after the FAB"
  and suit final actions such as save. Tonal is the middle ground, outlined is
  "medium-emphasis", and text buttons are for the "lowest priority actions"
  [S1523]. Toggle icon buttons cover on/off [S1523].
- **Apple HIG** [S1521]. The button roles are normal, primary, cancel and
  destructive.
  - "Keep the number of prominent buttons to one or two per view."
  - "Use style — not size — to visually distinguish the preferred choice."
  - Never give a destructive action the primary role.
  - An ellipsis means the button needs more input.
  - Targets are 44×44 pt.
  - "Outside of a list, use a button that behaves like a toggle."
- **Carbon:** "Each page should have only one primary button", and optional
  destructive actions use the tertiary or ghost danger style [S1535].
  **GOV.UK:** "Avoid using multiple default buttons on a single page" [S1534].
- **NN/g on confirmation:** "If you warn people too much, they stop paying
  attention". So prefer undo, and confirm only serious, irreversible actions
  [S1526]. Switches "should take immediate effect" [S1526]. An NN/g article on
  primary versus secondary buttons was not found.
- **Ark and Park UI:** Ark has no Button primitive. Its Toggle is "a two-state
  button" with `data-state` on/off [S1536]. Park UI, the styled layer over Ark,
  has one Button with a variant prop (solid, surface, subtle, outline, plain),
  sizes and `loading` [S1537].
- **WCAG 2.2:** SC 2.5.8 asks for targets of at least 24×24 CSS px [S1374]. SC
  1.4.11 asks for 3:1 contrast on component states [S1531].

**Colour grammar, one meaning each** (the actions study's proposal;
[RA-27c](RA-27c-visual-foundations.md) §3.4 revises it, so amber keeps four
uses: the primary, the live look, a held cue and an armed trigger):

| Look | Means |
|---|---|
| solid amber | do this next (primary) |
| tonal amber (`--accent-soft` fill with an amber edge) | on, selected or live |
| amber dot | changed |
| red text or outline | removes or darkens |
| red fill | armed |
| neutral outline | secondary |
| plain `--text` | tertiary |
| `--muted` | labels only, never pressable |
| pulse | busy |
| 40% opacity | off (dashes are dropped) |

**Components** (`ui/common/`):

```tsx
<Button variant="primary"|"secondary"|"tertiary" tone?="danger"
        confirm?="again to delete"   // two presses (useArm inside)
        busy?                        // aria-busy, pulse, presses ignored
        reason?="why it is off"      // aria-disabled; a press shows it in the region's note
        icon? block? shortcut? onPress />
<IconButton label="…" … />            // square; aria-label required
<ToggleButton pressed confirmOff? />  // Ark Toggle; on = tonal
<Chip selected />                     // Ark ToggleGroup item
<Disclosure expanded />               // tertiary + turning chevron, aria-expanded
```

- Where a setting has a label in a row, the existing `Switch` stays.
- Size needs no prop. `--target` already meets SC 2.5.8 [S1374] and Apple's
  44pt [S1521], and `block` gives full width.
- New tokens: `--on-accent` (= `--bg`) and `--surface-2` (the fill of a chip at
  rest).
- Contrast (computed): amber on the page is about 8.6:1, and danger text about
  7:1. A selected chip keeps its amber edge, because the tonal fill alone is
  about 1.7:1.
- Light theme: out of scope. `theme.css` is dark-only by choice (a dark room),
  and semantic tokens keep a light theme possible.

**Rules:**
- At most one primary per region: the deck, the look block, the layers, a
  layer's knobs, a slot panel [S1535][S1521].
- A primary shows only while it can act.
- A destructive action is never the primary [S1521].
- A phone shows at most two primaries at once.

**Assignments:**

| Element | Becomes |
|---|---|
| surprise | primary (RA-27b changes this to secondary) |
| like this | secondary |
| keep | removed: the header save does its job, and `k` presses it (inference; the maintainer decides) |
| saved look, pattern pick | Chip (live or picked = selected) |
| look header save | primary, shown only when there is something to save |
| save… | Disclosure `⋯` (look options) |
| editor save | primary; becomes `replace` with `confirm` when the name belongs to another saved look |
| delete, remove, remove stop | tertiary, danger tone (`confirm` on delete and remove) |
| revert, reset all | tertiary with `confirm` |
| in idle cycle | Switch |
| include master | checkbox (a form option) |
| + layer, catalog card | secondary with a + icon; `reason` when full |
| + example, add stop | tertiary with a + icon |
| ▲ ▼, master − + | IconButton secondary |
| ✕, ? shortcuts | IconButton tertiary |
| replace with pattern, more, every ? | Disclosure |
| triggers arm | ToggleButton with `confirmOff` |
| layout, input ends, single-key shortcuts | ToggleButton |
| blackout | secondary, danger tone, `block`, `confirm` (RESTORE keeps its neutral 2px outline) |
| cues | secondary with `reason="arm first"`; the held cue is tonal |
| segment knobs | the indicator changes from solid to tonal |
| scan, blink | the primary of their panel |
| use for board | secondary with `confirm` |
| reset dot, health chip, tags, banner, accordion and NumberInput parts | keep their own components, with the same tokens |

Replaced or wrapped: `TwoTapButton` becomes `Button confirm`; `AboutButton`
becomes `Disclosure`; `.quiet` and `.primary` become variants; `.step` becomes
`IconButton`; `.look` and the ToggleGroup items become `Chip`.

**The save fix.**
- One verb in one place. While the look is changed, or a made look plays
  unsaved, the header shows `[[save]]`. One press saves under the current name,
  or under the name offered.
- Saving over the same look takes one press, because routine confirmations stop
  working [S1526]. This changes behaviour, so the maintainer should confirm it.
- A name that belongs to another saved look turns save into `replace`, which
  takes two presses.
- While `⋯` is open, the header save hides.

**Before and after.** Key: `[[x]]` primary · `[x]` secondary · `x` tertiary ·
`(x)` chip · `((x))` selected/on · `!x` red · `●` changed.

Desktop side panel, before:
```
                                           [BLACKOUT]
master ━━━━━━━━━━━━━●━━━━━━━   [−] 60% [+]
[copper-tide ↻] [depth-charge ↻] [ember-fountain ↻]
[firefly-ink ↻] [lorenz-lantern ↻] [ember] [prism]  ← live: amber outline
[surprise] [like this] [keep] ?       [fade: saved ▾]  ← grey fill
firefly-ink ●                        revert  save…    ← muted like labels
 [firefly-ink________] [overwrite] delete            ← 2 presses, red
 ☑ include master   ☑ ↻ in idle cycle                ← 2nd acts at once
```

Desktop, after:
```
                                          [!BLACKOUT]
master ━━━━━━━━━━━━━●━━━━━━━   [−] 60% [+]
(copper-tide ↻) (depth-charge ↻) (ember-fountain ↻)
((firefly-ink ↻)) (lorenz-lantern ↻) (ember) (prism)
[[surprise]]  [like this]  ?             fade [saved ▾]
──────────────────────────────────────────────────────
firefly-ink ●                    revert   [[save]]  ⋯
```

`⋯` open:
```
firefly-ink ●                                       ⋯▾
 [firefly-ink_______________] [[save]]  ☐ include master
 ↻ idle cycle ((on))                         !delete
```

Phone, before and after. After: revert moves into `⋯`, and the name truncates
first.
```
firefly-ink  [fade: saved ▾]  save…    firefly-i… ● [fade ▾] [[save]] ⋯
 …knobs…                               …knobs…
[ember-fountain ↻] [firefly-ink ↻]     (ember-fountain ↻) ((firefly-ink ↻))
[surprise] [like this] [keep]  ?       [[ surprise ]]  [ like this ]   ?
master ━━━●━━━  [−] 60% [+]            master ━━━●━━━  [−] 60% [+]
[         BLACKOUT          ]          [        !BLACKOUT          ]
```

Layer row, before and after (the same on a phone, at 44px):
```
layers                     + layer     layers                  [+ layer]
▾ ink custom · 3 steps   100% (on)     ▾ ink  custom · 3 steps 100% ((on))
  particles → diffuse → palette          particles → diffuse → palette
  replace with pattern…                  replace with pattern ▸
  opacity ━━━━━━●  [−] 100.0 [+]         opacity ━━━━━━●  [−] 100.0 [+]
                 [▲] [▼]  remove         [▲] [▼]                 !remove
```

Moving the arrows away from remove means a slip on a move cannot arm a removal
(inference).

The three studies disagree on the rank of surprise, the verb style, keep,
`save…`, revert, the glyphs and amber "on". [RA-27b](RA-27b-control-page-proposal.md)
§6 settles each: surprise is secondary; the verbs are secondary buttons; keep
and `save…` become one `save`, with save as new… under its `▾`; revert goes in
the look menu; the glyphs are SVG icons beside their words; and "on" is
neutral.

### 11. UI review loop findings

Two loops reviewed the built page in Playwright, on desktop and on 320–414 px
phones: eight review rounds on `fx-ui-polish` before the redesign (merged
into `fx` in 16bacfe), and two pixel-polish rounds on `fx-polish` after
redesign phase 1b (merged in 861c406). Each fixer handled every finding
(fixed, partly fixed, or skipped with a reason) and ran `just check` before
each commit. The raw findings were working files, not kept. The review loop
counts findings a skeptic re-observed; measurements are from the fix reports.

#### 11.1 Review loop

Lenses: craft, disclosure, interaction, structure.

| Round | High | Med | Low | Fix commits |
|---|---|---|---|---|
| 1 | 5 | 17 | 24 | 14aecf8, dc78538, 8853368 |
| 2 | 2 | 17 | 31 | 9bd2c83, 16ef356 |
| 3 | 2 | 17 | 30 | f3f50f4, 59f4555, dc6861d, 90fbbad |
| 4 | 8 | 6 | 38 | d22fcd1, 9534e50 |
| 5 | 0 | 16 | 31 | e24c1ab, 9ca7884 |
| 6 | 2 | 4 | 47 | 6e4176b |
| 7 | 2 | 9 | 24 | 9234b80 |
| 8 | 1 | 11 | 22 | b1fb760 |

**Recurring themes.**
- **Touch.** A swipe meant to scroll changed a live knob (rounds 1 and 4).
  A first tap on a knob's ? was lost and a second reset the knob, since
  focus showed ↺ there (round 4). At 390×844 the editor held about one knob
  (round 4). Below about 384 px, BLACKOUT shrank under its word (round 6).
- **Edits lost without a guard:** a program replaced (round 1), a tap on
  another look (round 3), the idle cycle (round 7). Typing a name after
  "save as…" pressed the one-key shortcuts on the live room (round 8).
- **One sign, two meanings.** One amber dot meant both "changed" and "not
  the default" (round 2).
- **Edges.** Most low findings were misaligned steppers, units and ?s.
- **Page size.** By round 5 the page had 130 bytes of its gzip budget left;
  round 6 dropped Ark's colour picker for plain sliders (221,020 to 197,701
  bytes).

**The fixes that matter most.**
- The document never scrolls, with a test that it is the window's height
  (14aecf8).
- Room bars read as light: lit pixels on the desktop canvas went from 5.3%
  to 28.7% (dc78538).
- The dot means "differs from the saved look", from `looks.saved` on the
  wire (9bd2c83).
- A second press before a recall, surprise or like-this over unsaved edits
  (f3f50f4); the idle cycle waits for them (9234b80); "save as…" focuses
  its name box and no shortcut fires from it (b1fb760).
- A phone deck of three rows: the editor went from 209 to 366 px at
  390×844, and the ? never moves (d22fcd1).

**Engine and wire.** `aura` gained `looks.saved`, each look's fade and each
node's inputs (round 2), and the idle timings and cues (round 6); round 7
added the `fade` and `front` messages. Help, gists and refusals were
rewritten in a person's words (9ca7884, rounds 7–8); goldens were
regenerated.

**Skipped as new engine features:** reordering and renaming looks, a
route's depth, and a way back through made looks; most are in
[RA-27b](RA-27b-control-page-proposal.md) §7 phases 2 and 3.

#### 11.2 Pixel polish

The maintainer, after phase 1b: "the font sizes we're using are a bit too big, and the
padding everywhere is looking real funky" ([RA-27c](RA-27c-visual-foundations.md)
§3.1). Lenses: measure, design.

| Round | High | Med | Low | Fix commit |
|---|---|---|---|---|
| 1 | 13 | 20 | 10 | fa222f3 |
| 2 | 8 | 19 | 10 | 25ce0a8 |

**Type ramp,** size/line height in px, set in round 1 (fields stay 13 with a
mouse, 16 under a finger):

| Pointer | Look name | Title | Body | Caption |
|---|---|---|---|---|
| mouse | 22/27.5 → 18/24 | 16 → 15/20 | 14/19.6 → 13/18 | 12/16.8 → 11/16 |
| finger | 24/30 → 20/26 | 20 → 17/22 | 16/22.4 → 15/20 | 13/16.25 → 12/16 |

**Spacing.**
- Round 1: a container spaces its children (knobs 12 apart, no padding of
  their own). Desktop knob pitch 69 → 62 px, deck 337 → 280; phone knob
  108 → 96, deck 236 → 220, top bar 52 → 44. Phone controls are drawn 40
  px with 44 px targets.
- Round 2: a heading sits 8 above its content everywhere (10 to 25 before);
  a phone knob's label sits 4 above its control (14), and knobs are 12
  apart (22). All digits end at one x, trailing ⋯, ✕ and ? end on the
  column's edge, and the open layer lost its card. RA-27c §3.1 to §3.3 hold
  the rules.

**Calls left for the maintainer,** both applied and waiting on confirmation:
- **r2-d-1:** secondary buttons get a quieter edge, `--border-control`
  (about 1.6:1); fields and the value well keep `--border-strong` (RA-27c
  §3.3). That a labelled button needs no 3:1 edge is inference from WCAG
  1.4.11 [S1531], not re-read.
- **r2-m-16:** "+ layer" is one word button in every look; a one-layer
  look has no layers heading (§7), so there it ends the row under the
  knobs.

Round 1's trade-offs: value boxes are wider than their numbers, to match
blackout's width, and the phone slot shows two whole knobs, not three.

### 12. Modulators: terms and page copy (2026-11-06)

The maintainer's words (2026-11-06, verbatim, one message per paragraph), on the heading
"what moves the knobs":

> "what moves the knobs" needs a better one or two word name.
>
> why not "Modulators"
>
> use it. and spin up a subagent to make sure there's a very clear, concise
> tooltip or other progressive disclosure type thing that explains what this
> Modulators are. it should seach the web to see what common terminology is.
> it's okay if it's a little jargony, as long as it's common jargon and not new
> jargon to this system, and as long as it's concisely explained in a way a
> new, tech-savvy user could pick up quickly.

The study read the modulation docs of 13 products on 2026-11-06. A count is the
number of products whose docs use the word. Code facts here are at 16bacfe on
`fx`; page paths are relative to `web/src/` and engine paths to `src/pewpew/`.
This section replaces the "motion" words of §8 (updated there) and of RA-27b,
per the maintainer's decisions in [RA-27b](RA-27b-control-page-proposal.md).

#### 12.1 The word

- **"modulator" is the common name;** 10 of 13 products use the modulat-
  family. Bitwig files its sources under "Modulators" [S1650], and Ableton
  calls its LFO, Envelope Follower and Shaper "a modulator device" [S1652].
  Massive X [S1660] and Chromatik [S1666] have "Modulators" pages. In Logic, a
  knob "can be modulated by as many as ten modulators" [S1657]. Kilohearts says
  "modulator module" and "modulation source" [S1662]; Vital [S1654], Serum 2
  [S1656] and Pigments [S1661] say "modulation".
- **The exceptions:** Resolume says "parameter animation" [S1665];
  TouchDesigner has no umbrella word, since each source is a CHOP [S1664]; the
  OP-1 calls every source an "LFO", MIDI and "crank" included [S1663].
- **Modulation is relative.** Ableton's automation envelopes "define the
  absolute value of a control", while its modulation envelopes "can only
  influence this defined value" [S1653]. pewpew's routes work the same way: a
  route adds `depth` times the signal to the knob's own value
  (`fx/ops/signal.py`, module docstring).
- **The products' one-liners** say what modulation does to a parameter and, at
  most, name example sources (inference). Bitwig: "modulation is the idea that
  one component can influence another in a controlled way" [S1651]. Chromatik:
  "Nearly every parameter in the application can have its value automatically
  modified by algorithmic or interactive inputs" [S1666]. Pigments: "Modulate
  practically any parameter with anything you choose" [S1661].

#### 12.2 The seven kinds

The ids stay; only the page names change.

| Code id | Page name | Evidence | Help-sheet line (≤12 words) |
|---|---|---|---|
| lfo | **LFO** | "LFO" in 11 of 12, e.g. Bitwig [S1650], Ableton [S1652], Logic [S1657][S1659], Massive X [S1660], Kilohearts [S1662], TouchDesigner [S1664], Chromatik [S1666]; Resolume: not found [S1665]. An LFO runs usually below 20 Hz, "a rhythmic pulse or sweep" [S1669]. | Low-frequency oscillator: a slow repeating wave |
| walk | **random** | "Random" in 8: Bitwig's "tempo-synced random low-frequency oscillator" [S1650], Massive X's "Random LFO" [S1660], Pigments [S1661], Kilohearts [S1662], Logic's LFO shape [S1659], Chromatik's Randomizer [S1666], Vital [S1655] and the OP-1 [S1663]. Noise in 2 [S1666][S1654]; Chaos in Serum 2 [S1656]. "Drift": not found. | Glides between random levels, the same each time the look plays |
| beat | **beat** | Tempo sync in 4: Bitwig [S1650], Logic's "Sync button" [S1659], Serum 2's envelope BPM option [S1656], Resolume's "BPM Sync" [S1665]. "Beat" in 2: Bitwig's "Beat LFO" [S1650], TouchDesigner's Beat CHOP [S1664]. | Tempo-synced: pulses, climbs or falls with each beat |
| env | **envelope** | "Envelope" in 10, e.g. Bitwig [S1650], Ableton [S1652], Logic [S1657], Massive X [S1660], TouchDesigner [S1294], Chromatik [S1666]; ADSR in 5. | Rises then falls on each beat or other pulse |
| band | **audio follower** | "Envelope follower" in 4: Ableton [S1652], Bitwig [S1650], Logic [S1657], Minimal Audio [S1667]. Kilohearts says "Audio Follower" [S1662]; sidechain in 2 [S1650][S1661]; Resolume uses audio analysis (FFT) [S1665]. | Follows the music's loudness, or just its bass, mid or high |
| knob | **macro** | "Macro" in 7: Ableton's Macro Controls [S1512], Bitwig [S1650], Vital [S1655], Serum 2 [S1656], Pigments [S1661], Kilohearts [S1662], Chromatik's "Generic mappable macro knobs" [S1666]. | One knob you turn that moves several others at once |
| smooth | **smooth** | No consensus: Chromatik's Smoother [S1666]; Lag in TouchDesigner [S1664]; slew limiter or lag generator [S1668]. "Lag is also known as glide, slew or portomento" [S1670]. | Slew: turns another modulator's jumps into glides |

- "audio follower" keeps the word "envelope" to one kind, and "lag" reads as
  delay (both inference).
- The names §8 proposed (wave, wander, swell, glide, sound) were not found as
  modulator names in any of these products.
- Two lines rest on the code. An envelope's input counts as on at 0.5 or more
  (`Env.sample` in `fx/ops/signal.py`). A recalled look starts its modulators
  fresh (`compose/compositor.py:327-331`), and a random draws from a stream
  keyed by the signal and the step, so it wanders the same way each time
  (`fx/ops/signal.py`, module docstring).
- Vital's "random" and "amount" rest on a course lecture [S1655], not on
  Vital's docs. Serum 2's matrix wording and Logic's Smart Controls were not
  verified.

#### 12.3 The ? note, the knob line and depth

- **Heading:** modulators, in lower case like every label (§8 copy rule 3).
  Bitwig [S1650], Massive X [S1660] and Chromatik [S1666] title their pages
  "Modulators".
- **? note** (12 words): "A modulator keeps a knob moving: a wave, the beat, the
  music". Like the products' one-liners, it says what a modulator does to a
  knob and gives examples [S1661][S1666]. That a modulator works from your
  setting [S1653] goes in the ± entry, and the ± on the knob line shows it.
- **Help sheet** (one strings file with the notes, §8): **modulator**, with
  the ? note's line; **±, +, −**: "How far a modulator moves this knob; saving
  keeps your setting"; then the seven kinds (§12.2).
- **Knob line:** `modulated by ‘breath’ ±0.2 Hz`, Logic's phrasing [S1657].
  Several join with "; ", and a route into a part reads `on h ±60°`. The kind
  moves to the modulator's row, and the line has no ◆.
- **Sign.** It follows the ranges in the `fx/ops/signal.py` docstring. An LFO,
  a random, or a smooth of either swings both ways and shows ±. An envelope,
  beat, audio follower, macro, or a smooth of one of those moves a knob one way
  only and shows the route's own sign, + or −. This fixes a bug: `movedBy`
  drops the sign with `Math.abs` (`domain/stack/stack.ts:271,288`), so a macro
  set to −0.3 on opacity reads ±0.3.
- **Word: depth,** where one is needed (aria labels; the knob shows only the
  sign). It is the code argument and `docs/authoring.md` uses it. Both words
  are common: Logic labels the control "Depth" [S1657][S1658] and explains it
  as "amount it affects the target" [S1657]; Kilohearts uses both [S1662];
  Bitwig mostly says "modulation amount" [S1651]. "amount" already labels nine
  step knobs (`fx/ops/color.py:60,81`, `fx/ops/combine.py:68,79,90,100,115`,
  `fx/ops/coord.py:67,140`), so a ± called amount beside one would read
  "amount, amount".
- **The connection** gets no noun on the page. If one is needed, **mapping**,
  as in Ableton [S1512] and Chromatik [S1666]; others say routing
  [S1651][S1658][S1661] or a mod matrix for the table of them [S1656][S1658].

#### 12.4 The ? as a disclosure

The ? is an APG disclosure [S1530], as in §8:

```html
<h3 id="mods-h">modulators</h3>
<button type="button" class="quiet about" aria-label="about modulators"
        aria-expanded="false" aria-controls="mods-note">?</button>
<p id="mods-note" class="note" hidden>A modulator keeps a knob moving: a wave, the beat, the music</p>
```

- The button follows the `h3`, so the heading's name stays "modulators". Its
  name matches "about master" (`ui/deck/Master.tsx:64`).
- `aria-expanded` replaces `aria-pressed`. The note stays in the DOM, hidden,
  so `aria-controls` resolves. There is no live region.
- Esc or a second press closes it, focus stays on the ?, and one note is open
  page-wide.

#### 12.5 Changes to build

Engine labels (`fx/ops/signal.py`; ids stay):
- `Walk` gets `label = "Random"`, since an op with no label shows its id
  capitalised (`fx/op.py:327-328`); `Band` gets `label = "Audio follower"`;
  `KnobOp` changes "Knob" to "Macro".
- `Env`'s help, which the page shows: "while its trigger stays on" becomes
  "while the pulse lasts", and "once its trigger lets go" becomes "after the
  pulse ends".
- Then `uv run pytest --regen-goldens`, reviewing the catalog diff.

Page:
- Delete `SIGNAL_KINDS` (`domain/stack/stack.ts:73`), so the engine labels are
  the only list of names, and drop `signalKind`'s `toLowerCase()`. Its callers
  are section heads, which the CSS already lower-cases, so exempt "LFO" there.
- `movedBy` reads "modulated by ‘id’", with the §12.3 sign rule.
- `ui/params/ParamPanel.tsx:160`: "what moves the knobs" becomes "modulators",
  with the ? note.
- Update the stack, wire and params tests, then `just web`.
- Adding and connecting modulators on the page needs an engine message, and
  `infra/wire/protocol.ts` has none: a separate change.
- The field op `modulate` (`fx/ops/combine.py:108`) shows as the step
  "Modulate" and reads as a modulator (inference). Relabel it, for example
  "Ripple", the word its docstring uses.

#### 12.6 Not settled

- **No live audio source was found.** The runner reads `FakeFeatures`
  (`run.py:192`), which gives seeded sine bands and a beat fixed at 120 BPM
  (`features.py`, the `beat_phase` field). So "the music", in the ? note and
  the audio follower's line, describes intended behaviour. The maintainer should confirm
  it before the copy promises sound.

### 13. Shuffle control (2026-11-08)

The maintainer asked on 2026-11-08 for control over whether the lights stay
on one look or rotate, and how long each look plays; the build brief stated
the ask, and the maintainer's own words were not kept. Before it, the page
showed the idle cycle's timings as text only (`cycleText`, `web/src/aura/looks.ts`
at 15ade80).

- **Decision.** One `shuffle` toggle at the end of the make row: one press on,
  one off, the off state holding the look. Spotify's shuffle is a toggle by
  the play controls [S1556]; the make row already holds what lets pewpew pick
  what plays (inference). On, a line under the row counts down to the next
  look, and its `every 2 min ⌄` opens two lists, each look and starts, set
  inline as Figma moved blend mode into an inline dropdown [S1573]. Each choice
  writes the looks file at once, as a look's fade and shuffle flag do, since
  the one-press save keeps a look and these are not part of one (RA-27b,
  Decisions item 2).
- **Right away** is a wait no longer than a turn: after a touch the look plays
  one turn and shuffle goes on, through the engine's existing idle wait, so no
  second mechanism (`pewpew.aura.book`). Rounds, end, weights, window and fresh
  stay in the file: an operator choosing hold or rotate does not need them
  (inference).
- **New words.** "untouched" names the idle wait in one word, from the page's
  earlier "with nobody touching anything"; "idle" stays a code word, as
  "shuffle" replaced "idle cycle" on the page (§8). "right away" and "each
  look" are plain English. Both rows are in the glossary.

## Verdicts

These rate each source family as a UX reference for pewpew's page, not as
technology to build on. Maintenance status was not researched for any product
here.

- **Design systems and guidelines** (Apple HIG [S1521][S1522], Material 3
  [S1523], Carbon [S1535], GOV.UK [S1534], NN/g [S1524][S1525][S1526], W3C
  WCAG and APG [S1531][S1530][S1374]): **stable**. These are the primary
  references for actions, disclosure and accessibility, and they are
  research-led sources of the kind the maintainer asked for.
- **Pro creative tools** (Resolume [S1500][S1501], Ableton [S1512], Figma
  [S1527], Lightroom [S1515], Procreate [S1516], Komplete Kontrol [S1513]):
  **stable** references for the specific patterns cited.
- **Lighting consoles** (grandMA3 [S1508], ChamSys [S1509], Onyx [S1510], ETC
  [S1511]): **stable** references for keeping a store apart from a performance
  surface at scale. Their hardware-key verbs transfer only partly to a phone
  page (inference).
- **Design-led products** (Spotify, Linear, Figma, Vercel/Geist, Superhuman;
  §9): **stable**, and the primary model for the page, by the maintainer's direction.
  Linear [S1562], Spotify [S1560] and Figma [S1574] changed the cited
  surfaces in 2026; Geist's and Superhuman's dates were not researched.
  Figma's SDS is MIT [S1577].
- **WLED** [S1503][S554][S1504][S1505]: **not a model** for the page, by the maintainer's
  direction (§9.4). Its facts stay recorded.
- **Synth and DAW modulation docs** (Bitwig [S1650][S1651], Ableton
  [S1652][S1653], Logic [S1657], Kilohearts [S1662], Massive X [S1660] and the
  others in §12): **stable** references for modulation words, which these
  tools share. They were read for words only.
- **LED and VJ engines** (Chromatik [S1265][S1506], MilkDrop [S1502],
  Pixelblaze [S552], MadMapper [S1507]): domain analogues for cycle, modulation
  and preset traversal. Whether the maintainer's WLED critique extends to them is an open
  question.

## Code-reading queue

1. **pewpew's page at the current `fx` head.** Every line cited here is at
   8853368. Re-run the four audits (looks, nesting, words, actions) and
   RA-27c's measurements once `fx-ui-polish` lands, before building on a
   line.
2. **The design-led study's gaps** (§9.5): a public Encore or Linear button
   spec; Linear's peek and empty-state docs; Geist's breadcrumb menu
   behaviour; Superhuman's help centre (403); Figma's Config 2024 UI3 talk.
   Reading Figma's SDS `Button` states beyond its variants [S1577] would
   settle the tier styles.
3. **Gaps the studies could not close:** the projectM frontend's controls (its
   README does not list them); ChamSys playback page text; an official
   Pixelblaze web UI doc; tagging in any VJ/LED tool; official Serum 2 or Vital
   docs on favourites or random; Lightroom solo mode (Adobe help returned 403);
   Logic channel strips; Notch. The Onyx Cuelist Directory page's full URL was
   not re-resolved [S1510].

## Open questions

From page-ia, with its defaults:
1. Do looks often pass about 6 layers? Default: no, so nest in place. If yes,
   revisit the inspector (§7 B).
2. "surprise me / vary this", or the shorter "surprise / vary"? Default: the
   longer pair, shortened only if the phone header overflows.
3. A "?" on every knob that has help, or only on the unclear ones? Default:
   every knob with help (most have it). If that looks noisy, make the knob label
   the tap target, with a dotted underline.
4. Should steps start closed? Default: closed, with the device remembering what
   you open. The main knobs cover live play.
5. Rename "master" to "brightness"? That changes the top bar, the shortcuts and
   the docs. Default: yes; on a phone the top bar shows only "70%".

From actions:
6. Should the deck's keep go, with `k` pressing the header save? (The maintainer decides.)
7. Should saving over the same look take one press? (The maintainer should confirm.)

Raised by the maintainer's direction:
8. Does the maintainer's critique of WLED as engineer-designed extend to the other LED and
   VJ engines used here (Chromatik, MilkDrop, Pixelblaze, MadMapper)? Not
   settled. RA-27b rests no recommendation on them, and its "motion at both
   ends" is now inference, so the answer no longer blocks the page.
9. Which WLED-tagged items survive the design-led study? Settled in §9.4.

Raised by the modulator study:
10. Will a live audio source feed the audio follower and beat? The ? note's
    "the music" promises it, and the runner reads `FakeFeatures` (§12.6).

[RA-27b](RA-27b-control-page-proposal.md) §8 lists the decisions for the maintainer, and
[RA-27c](RA-27c-visual-foundations.md) lists four visual ones.
