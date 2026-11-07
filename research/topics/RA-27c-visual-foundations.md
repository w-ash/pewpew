# RA-27c: Control page, visual foundations

Last researched: 2026-11-05
Status: draft. The four choices §3 left to the maintainer are settled or built (Open
questions).
S-ID block: S1600–S1649 (S1600–S1639 used). It also cites S1374, S1524,
S1525, S1531, S1535, S1561, S1563 and S1579 from earlier blocks.

This study asks why the control page reads flat, and sets the visual
foundations that fix it. §1 states the fundamentals of visual hierarchy, §2
measures the page against them, and §3 turns them into tokens. §3 keeps the
action hierarchy of [RA-27](RA-27-control-page-ux.md) §10 and the design-led
patterns of RA-27 §9.3. [RA-27b](RA-27b-control-page-proposal.md) builds the
final proposal on §3.

## Reading notes

- **Three notes ran on 2026-11-05:** principles, audit and foundations. A
  review revised the foundations before this record. This doc rewrites them.
- **Code facts describe the preview commit 8853368 on `fx-ui-polish`.**
  `fx-ui-polish` is still changing the page (its head was 90fbbad on
  2026-11-06), so re-read a line before you build on it. Page paths are
  relative to `web/src/`. A bare `theme.css` is `ui/theme.css`, the page's only
  stylesheet (`app/main.tsx:6`).
- **Measurement.** Tokens were read from `theme.css`; spot checks matched the
  CSS served at :8765. Rendered values are Playwright computed styles and boxes
  at 1440×900 (mouse) and 390×844 (touch). Every page→engine message was
  dropped (0 sent), and clicks only opened disclosures. The idle cycle rotated
  the look: the desktop screens show `depth-charge`, the phone screens and box
  measurements `lorenz-lantern`. Not captured: the health panel, layout mode,
  armed and cue states, and the lost banner. The tree holds no binary assets,
  so the screenshots and measurement files are not kept: the text says what
  each one showed.
- **Contrast ratios** use the WCAG 2.2 formula [S1632], computed by the
  study's scripts (not kept).
- **Refactoring UI** cites name chapter titles from the book's public table of
  contents [S1607]; the chapter text was not read.
- **Material.** m3.material.io renders only with JavaScript, so the principles
  cite the Android and GitHub docs [S1610][S1611][S1612][S1613]. The audit
  rendered the m3.material.io pages with Playwright [S1614][S1615][S1616]
  [S1617]. Apple's HIG text came from Apple's JSON. The audit checked each of
  its quotes against the fetched page text.
- "(inference)" marks the study's own reasoning.

## Key questions

1. What makes visual hierarchy work on a dense control page? (§1)
2. How does the page at 8853368 rank its content, measured? (§2)
3. Which tokens and rules fix it, and what does each choice cost? (§3)

## Findings

### 1. Principles of visual hierarchy

Each point gives the rule, then why, then the source.

#### 1.1 Emphasis tools

- **Rank first, style second.** Mark each element primary, secondary or
  tertiary before styling it, since hierarchy is the order "of intended
  importance" [S1525].
- **The tools.** Value contrast: "not the actual color … but rather the
  contrast in value and saturation" [S1525]. Scale [S1525]. Weight, size and
  colour [S1618]. Grouping by proximity or enclosure [S1525]. Position: top and
  leading side first [S1619]. Space: extra space around an element makes it
  seem more important [S1639].
- **Order of strength.** Not found in any source read. (inference) On a dense
  dark page: value contrast > size > weight > position > space > containment >
  hue. Hue comes last because colour alone fails some users [S1633].
- **Emphasize by de-emphasizing.** Quiet what competes with the primary instead
  of making the primary louder (Refactoring UI, "De-emphasize to emphasize"
  [S1607]). Linear dimmed its sidebar so task content can "stay in focus" while
  navigation "should recede" [S1561]. "If everything is emphasized, then
  nothing is emphasized" [S1628].
- **Budgets.** At most 3 sizes, 2 big elements and 3 contrast variations
  [S1525]. Size is not the only lever ("Size isn't everything" [S1607]).
- **Test.** Blur the screen 5–10 px. The groups and the focal point must
  survive [S1525].

#### 1.2 Typography

- **Few sizes.** Use 2–3 type sizes per view [S1600]. M3 offers 15 styles, but
  "your product will likely not need all 15", and its example uses five
  [S1610]. (inference) A control page needs 4: hint or caps label, body or
  value, block title, view title.
- **Tested values.** Label 12/16 Medium, body 14/20 Regular, title 16/24
  Medium, large title 22/28 [S1610]. Text defaults to 17 pt on iOS (11 pt
  minimum) and 13 pt on macOS (10 pt minimum) [S1618].
- **Ratio.** A modular scale multiplies a base by one ratio [S1637]; M3's steps
  are hand-tuned [S1610]. (inference) Use about 1.2–1.25, since small screens
  punish large ratios. §3.1 takes one exception.
- **Line height.** Body text takes 120–145% of its size [S1623]. Line height
  tightens as size grows ("Line-height is proportional" [S1607]): M3 uses 1.43
  at 14 px and 1.27 at 22 px [S1610]. Single-line labels get less line height
  than multi-line copy [S1635].
- **Weights.** Use Regular to Bold, and avoid Light and Thin, especially when
  text is small [S1618]. In sans text, emphasize with bold, not italic
  [S1628]. (inference) Two weights, 400 and 600, are enough.
- **Caps labels.** Use caps only for labels shorter than one line [S1625], and
  add 5–12% letterspacing [S1624].
- **Values.** Use tabular figures (`font-variant-numeric: tabular-nums`) for
  numbers that change or align in columns [S1627][S1635].
- **Typefaces.** Use as few as you can: mixing many "can obscure your
  information hierarchy" [S1618]. (inference) One sans for UI text; mono only
  for code-like values.
- **Text roles** (inference, built on the sources above):
  - heading: the largest size in its region, 600, primary colour tier;
  - value: body size, 400–500, tabular figures, primary tier;
  - label: small or caps, 500, secondary tier;
  - hint: small, 400, tertiary tier.
- **Headings.** Mark a heading with space above and below and bold, at "the
  smallest increment necessary" in size. Use at most three heading levels;
  "Two is better" [S1626]. Style for importance, not for the HTML tag
  ("Separate visual hierarchy from document hierarchy" [S1607]).

#### 1.3 Spacing

- **Scale only.** For example 2, 4, 8, 12, 16, 24, 32, 40, 48, 64 [S1639];
  "Establish a spacing and sizing system" [S1607].
- **Space between groups > space within them.** Varying whitespace "to either
  unite or separate elements is key". Keep a label close to its field.
  Proximity can overpower similarity of colour or shape [S1601]. As space
  grows, the perceived relation weakens [S1639]. "Avoid ambiguous spacing"
  [S1607].
- **Mechanical rule** (inference). Each nesting level outward at least doubles
  the gap: 4 inside a knob, 8–12 between knobs, 24 between blocks, 32 or more
  between regions.
- **Rhythm.** The parent sets the gaps between its children (the owl selector
  or flex `gap`), not each child's own margin. Nest a small inner stack inside
  a larger outer one [S1638].
- **Start generous,** then remove space ("Start with too much white space"
  [S1607]).

#### 1.4 Grouping

- **Use space first, then a surface, then a line.** Whitespace alone "reduces
  the visual complexity". Use a container "when whitespace alone doesn't
  suffice". Common region can override proximity [S1525]. A background tint
  makes a common region without a border [S1630].
- **Similarity.** Same function, same look; different function, different
  look. "Same-color buttons will be perceived as sharing the same level of
  importance" [S1602].
- **Which tool where** (inference):
  - space: siblings of one kind, such as the knobs of a layer;
  - surface: a unit that is picked or acted on as one, such as a layer card or
    the editor panel;
  - divider: long lists of identical rows only, at soft contrast [S1561];
  - never all three on one boundary.
- **Borders cost.** Decorative borders "add clutter", and full-width segments
  make "false floors" [S1525]. Too many borders feel "busy and cluttered"
  [S1607]. Linear cut separators [S1561].
- **Nesting.** Indented items read as subordinate [S1619]. More than 2
  disclosure levels "typically have low usability" [S1524]. (inference) For
  look › layer › step › knob, each level gets one different cue: the look, the
  view title on the base surface; a layer, a raised row or card; a step, an
  indent under its layer; a knob, a label and value row. At most two levels
  are open at once.

#### 1.5 Alignment, grids, density

- **Few edges.** "People assume that aligned items are related", and
  indentation conveys hierarchy [S1619]. Linear aligned labels, icons and
  buttons on both axes [S1563].
- **Mechanical rule** (inference). Each column gets one left text edge, and its
  controls end on one right edge. Icons sit in a fixed-width column.
- **Labels and values** (inference). In a row, put the label on the left and
  right-align the value in tabular figures so the digits hold still [S1627].
  When stacked, put the label tight above its control [S1601].
- **Density.** iOS controls default to 44×44 pt and macOS controls to 28×28
  [S1622]. The WCAG floor is 24×24 CSS px [S1374]. (inference) Desktop is
  denser through smaller type and targets; the phone keeps the same ranks on a
  larger base.

#### 1.6 Surfaces and elevation in dark themes

- **Higher is lighter, not shadowed.** Surfaces "become lighter … at higher
  elevations", on dark grey, not black [S1613]. Dimmer base colours recede and
  brighter elevated ones advance [S1621]. M3 elevation is "mainly … tonal
  color overlays" [S1610].
- **How many levels.** M3 has one surface plus five containers, lowest to
  highest [S1611]. Geist has four on-page materials and four floating ones
  [S1636], and its second background is used "sparingly" [S1634].
  (inference) A control page needs 3 on-page levels (page, section, raised or
  picked item) and 1 floating level.
- **States are their own steps.** Geist gives default, hover and active
  separate background steps and separate border steps [S1634].
- **Example ladder** (inference; ratios by the WCAG formula): surfaces
  `#0b0b0e`, `#131317`, `#1b1b21`, `#24242b`; primary text `#ededf0` at least
  13.2:1 on all four; secondary `#a1a1aa` at least 6.0:1; tertiary `#8a8a93`
  4.51–5.74:1, so it passes as text; a `#6b6b76` control edge holds 3:1 only up
  to `#1b1b21`. §3.3 replaces this ladder.

#### 1.7 Colour roles

- **One accent.** Use at most "2 primary and 2 secondary colors" [S1525].
  Reserve colour for "status indicators or primary actions" [S1620]. Build
  8–10 greys and 5–10 shades of the primary colour, and use accents "pretty
  sparingly" [S1608]. Linear builds its themes from three inputs: "base color,
  accent color, and contrast" [S1563].
- **One meaning per colour.** "Avoid using the same color to mean different
  things" [S1620]. Reserve red for warnings and errors [S1525].
- **Hue-biased neutrals.** "Greys don't have to be grey" [S1607]. (inference)
  Tint every neutral slightly toward one base hue.
- **Text tiers.** Apple: label, secondary, tertiary, quaternary [S1620].
  Geist: step 1000 for primary text, 900 for secondary [S1634]. M3: on-surface
  and on-surface-variant [S1610]. Use 3 at most [S1525].
- **Coloured grounds.** "Don't use grey text on colored backgrounds" [S1607].
  (inference) Use a shade of the ground's own hue instead.
- **Minima.** Text needs 4.5:1, and large text (about 24 px, or 18.66 px bold)
  3:1 [S1632]. Component edges, states and focus indicators need 3:1, and
  inactive components are exempt [S1531]. For small text, "strive for … 7:1"
  [S1621]. Colour is never the only cue [S1633].

#### 1.8 Focal point and scanning

- **One focal point per region,** with at most 2 big elements [S1525]. The
  item that differs is the one remembered, so use "restraint" [S1631].
- **Order.** Put the most important items "near the top and leading side"
  [S1619].
- **Scanning.** Readers fall into the F-pattern "when there are no strong
  cues" [S1603]. In layer-cake scanning, eyes land on the headings, so style
  headings "in a consistent, predictable manner" and make clear which content
  each one owns [S1604]. Put the information-carrying words first [S1603].
- **Balance.** Spread visual signal evenly; area counts, not only the number
  of elements [S1600].

#### 1.9 Signifiers

- **Pressable looks pressable.** Flat controls "should look clickable even
  without heavier effects", and "Don't make nonclickable items look like
  buttons" [S1605]. Weak signifiers cost 22% more time [S1525].
- **Button tiers.** Filled: high emphasis, for primary actions such as "save".
  Outlined: medium emphasis, for alternatives. Text: low emphasis [S1612].
  (inference) One filled button per region.
- **States.** The states are enabled, disabled, hover, focus, pressed,
  selected and loading. Show focus with an outline, not colour alone. Selected
  "is not a button state". A disabled control stays readable at lower contrast
  [S1606].
- **Nouns vs verbs.** Elements that look alike are read as alike [S1602].
  (inference) Show saved items (looks) as rows or cards, and actions as buttons
  labelled with a verb.
- **One cue per meaning** (inference):
  - pressable: a shape (a fill, or an edge at 3:1) and a pointer cursor;
  - selected: a tint plus a second cue, such as weight or a check;
  - live: a cue unlike the selected one, such as a dot plus a word;
  - disabled: lower contrast and no hover.

#### 1.10 Failure modes

- Everything has the same weight, so nothing is the focal point
  [S1525][S1628].
- Too many borders add clutter and false floors [S1525][S1607][S1561].
- Colour carries a meaning alone, which fails WCAG 1.4.1 [S1633].
- Headings are smaller or quieter than labels, so layer-cake scanning has no
  anchors [S1604][S1626].
- Spacing is inconsistent, so the groups are ambiguous [S1601][S1639].
- Different functions share one style and are read as the same thing
  [S1602][S1620].
- More than 3 sizes or contrasts, so the levels blur [S1525].
- Signifiers are weak, so people hesitate [S1525].

### 2. Audit: the page at 8853368, measured

The page passes contrast but has almost no hierarchy. It uses 3 type sizes
about 1.15× apart, 2 text greys, one button style for most controls (42 of 94
control-sized elements on desktop, plus 12 number fields drawn the same), one
1.26:1 hairline as the only divider at every nesting level, and no surfaces.
Section headings are smaller than the content under them. A#n names problem n
of §2.4.

#### 2.1 Tokens as used

**Type.** The root is `13px/1.4 ui-monospace` (`theme.css:53`), 16 px on touch
(`theme.css:65`). One line height serves everywhere.

| Tier | Rule | Desktop / phone | Weight | Desktop text runs |
|---|---|---|---|---|
| Look title | `1.15em` (`theme.css:857`) | 14.95 / 18.4 px | 700 | 1 |
| Body | inherit | 13 / 16 px | 400 | 107 |
| Small | `--small: 0.85em` (24 rules) | 11.05 / 13.6 px | 400 | 28, **including both section headings** |
| Accidental | `.cap` inside `h2` (`ui/stack/LayerList.tsx:95`) | 9.39 px | 400 | "· top first" (the `em`s compound) |

- **2 weights:** `bold` appears in 6 rules.
- **2 families:** monospace everywhere; `system-ui` only for notes
  (`theme.css:207`).
- **4 letter-spacings,** applied to lowercase text in 3 rules (`theme.css`
  lines 849, 1009 and 1458).
- **6 `lowercase` transforms** (`theme.css` lines 917, 1010, 1218, 1381, 1391
  and 1449).

**Colour.** There are 7 opaque neutrals:

| Token | Value | Use |
|---|---|---|
| bg | `#0b0b0e` | page, input fill |
| panel | `#121217` | 1.05:1 against bg; used only for 4 floating notes (`theme.css` lines 352, 482, 935, 1598) |
| primary fill | `#2a2a33` | hard-coded, one button (`theme.css:158`) |
| line | `#23232b` | 12 `border-top`, 2 `border-left`, 5 other borders |
| line-strong | `#60606a` | every control edge |
| muted | `#8a8a93` | 27 rules; **77 of 137 rendered text runs (56%)** |
| text | `#ddd` | 12 rules; 55 runs |

`var(--accent)` (`#d99a2b`) appears in 23 declarations, plus the `--warn`
alias (a recount at 8853368; the audit note said 21). Red comes in 3 shades:
`#b91c1c`, `#f87171` and `#7f1d1d`.

**Space.** The tokens `--space-1…4` (4/8/16/24 px, `theme.css:32-35`) set only
17 of about 110 spacing values, and `--space-4` is never used. The rest are
hand-set rem values, and rem is 13 px on desktop. That gives **21 distinct
lengths**: 0.7, 2, 2.6, 3.2, 3.9, 4, 4.5, 5.2, 5.9, 6, 6.5, 7.8, 8, 9.8, 10,
10.4, 13, 15.6, 16, 23.4 and 26 px. Several are near-duplicates.

**Shape.** 10 radius values; border widths of 1, 2 and 3 px; 5 opacity levels
used as states (0.35 inert, 0.4 off, 0.5 pending, 0.55 layer off, 1); 1
shadow.

#### 2.2 Contrast

WCAG 2.2 minima: 4.5:1 for text [S1632], 3:1 for component edges and states
[S1531].

| Pair | Ratio |
|---|---|
| text on bg / panel / primary fill / accent-soft | 14.47 / 13.75 / 10.46 / 7.55 |
| muted on bg / panel | 5.74 / 5.46 |
| accent on bg; bg text on accent | 8.06; 8.06 |
| danger-text on bg; white on danger; banner | 7.11; 6.47; 10.02 |
| **control edge (line-strong) on bg / panel** | **3.16 / 3.00** (at the floor) |
| blackout edge `#b91c1c` on bg | 3.04 |
| **hairline** on bg; also the switch's off track (`theme.css:1177`) and swatch rings | **1.26** |
| **primary fill vs bg** | **1.38** |
| **text vs muted** (the only step between text tiers) | **2.52** |
| an off layer's `.runs` (muted × 0.55 opacity); the row stays operable | **2.49**: misses SC 1.4.3 (inference) |

Every tier is legible. The problem is 2 text tiers and surfaces 1.05:1 apart.
NN/g's limit is "no more than 3 contrast variations for complex designs"
[S1525]; this page uses fewer than that, too few to separate its levels
(inference).

#### 2.3 Region map and visual weight

**Desktop:**
- **Top bar (1440×32).** Name and master at 13 px/400, the same style as a
  button. The IDLE CYCLE tag is its only solid fill.
- **Canvas (917×868, 64% of the width).** The focal point by area. This is
  correct: it is the light.
- **Deck (516×216).** BLACKOUT, then master, then **13 identical chips in 4
  rows**, then the variety row (`ui/deck/Deck.tsx:35`). Every row gap is
  5–6 px.
- **Look panel (from y=249).** The title is 14.95 px bold. Knobs are 63 px
  tall with hairlines between them; signal sections are 24 px rows.
- **Layers, then layer knobs.** Headings 11 px muted; rows 25 px; the open row
  indented 9 px; step sections 13 px.

Likely eye order (inference, from isolation [S1631]): canvas highlights →
BLACKOUT (the only red, uppercase, bold) and the IDLE CYCLE fill → the orange
switches and the accent-outlined live chip → the uniform chip grid →
"surprise". The look title comes after 13 chips. The look's name appears 3
times in 3 styles: top bar, chip and title.

**Phone:** top bar 52 px, canvas 30svh, a scrolling slot, and the deck pinned
at the bottom (212 px). The look name gets **64 of 390 px** ("loren…"), while
the IDLE CYCLE tag gets 121 px. The red BLACKOUT (358×44) and the accent tag
frame the screen. The editor gets about 330 px, which fits three 108 px knobs.

#### 2.4 Top 10 hierarchy problems

**A#1. Saved looks, actions and steppers look the same.** On desktop, 42 of 94
control-sized elements render identically: transparent fill, 1 px `#60606a`
edge, `#ddd` text, weight 400. That covers 11 looks, "like this", the fade
select, master −/+, stepper buttons, "layout" and "ok". 12 number fields differ
only by a fill equal to the page colour. On a phone it is 52 + 17 of 101.
Spacing makes it worse: `.deck`, `.looks-row`, `.variety` and `.scroller` all
use `gap: 0.4rem` (`theme.css` lines 681, 730, 736 and 226), so "surprise /
like this / keep" sits 5.2 px under the chips, exactly the gap between chip
rows. It reads as a fifth row of looks (inference). Things that look alike are
perceived as one group [S1602], and proximity overpowers other cues [S1601].
M3 matches a button's appearance to its emphasis [S1614]; Geist has Default,
Secondary and Tertiary buttons [S1579].

**A#2. Save is the weakest control in its own header.** "save…" is a quiet
button with a transparent edge and muted text (`ui/deck/LookPanel.tsx:51`,
`theme.css:148-152`). On a phone the bordered `fade: saved` select beside it
outweighs it, and "saved" collides with "save" (inference). In the open
editor, save/overwrite uses the default outline, the same as a look chip,
while the accent-filled checkboxes (`theme.css:898`) are brighter. Refactoring
UI: primary actions "should be obvious… solid, high contrast background
colors" [S1609]. M3 keeps text buttons for "actions not essential to the user
journey" [S1614]. Weak signifiers cost users effort [S1525].

**A#3. Headings are smaller and fainter than their content.** `h2` is muted
and normal weight (`theme.css:77-83`), and block heads add `--small` and
0.08em tracking (`theme.css:846-851`). So "layers" and "layer haze" render at
**11.05 px muted, below everything they head**. Their step sections ("motion ·
kick") are 13 px (`theme.css:999-1011`), and knob labels are 13 px muted
(`theme.css:915-918`), the same style as the sections. Scanning depends on
headings that "visually stand out" [S1604]. Butterick: emphasize a heading with
space and bold [S1626], and don't letterspace lowercase [S1624].

**A#4. The type scale is flat.** Sizes run 11.05 → 13 → 14.95 px, steps of
1.15–1.18×; the title is 1.15× body; bold appears in 6 rules. M3 has 15
baseline styles from Display to Label [S1615]. Geist splits Heading (14–72),
Label, Copy and Button [S1635]. Every Layout derives a scale from a ratio; its
example uses 1.5 [S1637]. Refactoring UI suggests weight and colour over size
[S1609], but only 2 of each exist here. Monospace everywhere removes one more
lever. Butterick finds monospace "harder to read" [S1629], and Apple warns that
mixing typefaces obscures hierarchy [S1618]. Monospace is deliberate
(`theme.css:36`): a tradeoff.

**A#5. One hairline divides everything, with no surfaces.** `border-top: 1px
solid var(--line)` appears 12 times (`theme.css` lines 546, 683, 838, 907,
1005, 1347, 1414, 1444, 1496, 1539, 1550 and 1569). The same 1.26:1 line
separates slot, deck, block, knob, section, layer row, actions row and card.
`--panel` is never used as a container. Common region needs a boundary or
background [S1525]. Refactoring UI: "use fewer borders", and use background or
space instead [S1609]. M3 shows elevation as tonal surfaces [S1616]. Geist has
2 backgrounds and 3 component-background steps [S1634]. Linear derives
surfaces by elevation [S1563].

**A#6. Indentation does not show nesting.** Measured left edges:

| Element | x (px) |
|---|---|
| look knobs | 937 |
| layer rows | 937 |
| open layer body | 946 |
| "layer haze" block | 937 |
| its step sections | 937 |
| step knobs | 946 |

So look › layer › step › knob is drawn 9 px off the look's own knobs, in the
same `.param` style. The only cue is that 9 px, with a 1.26:1 rule
(`theme.css:1019-1020`). Apple: "use indentation to convey hierarchy"
[S1619].

**A#7. The accent means at least 8 things:** live look, pressed toggle, IDLE
CYCLE, changed dot, reset dot, layer switch, picked layer id
(`theme.css:1374`), route mark, focus, segment, checkbox, pending, fade and
held. The default desktop view shows 5 accent or red items at once. Isolation
works only when one item differs [S1631]. NN/g: "If everything is contrasted,
then nothing stands out" [S1525]. M3 gives each colour a role [S1617].

**A#8. The subject comes last.** On wide screens the order is blackout,
master, looks, variety (`ui/deck/Deck.tsx:35`), so the look title starts at
y=259. On a phone the name is truncated to 64 px. Apple: "place the most
important items near the top and leading side" [S1619]. Leading with blackout
is a safety choice (`ui/deck/Deck.tsx:10-13`); the problem is that nothing
ranks the look name (inference).

**A#9. Alignment edges break.**
- **Reset and changed dots** sit at 5 different x positions (975–1007),
  following label length. They jump to the far edge when a `now` readout takes
  `margin-left: auto` (`theme.css:948-951`).
- **Right edges** fall at 1389 (steppers), 1427 (selects, units, header
  actions) and 1430: the 40 px switch overflows its 34 px label
  (`theme.css:1170` against `theme.css:1362-1369`).
- **On a phone, the `now 7…` readout covers the stepper's "−"** by 62 px: the
  readout's right edge is at 214 and the stepper's left at 152 (the grid at
  `theme.css:1037-1055`).

Linear's redesign set out to "maintain visual alignment" [S1563]. Apple:
"People assume that aligned items are related" [S1619].

**A#10. Spacing has no scale, so it can't rank.** There are 21 ad hoc lengths,
and the deck uses one 5.2 px gap across four levels (A#1). Inside a knob the
gap is 2.6 px (`theme.css:905`). Between knobs it is 8+1+8 px; between blocks
8+16+1+8 px. A block break is therefore only about 2× a knob break, and both
carry the same line. That is too little to read as a different level
(inference). Proximity works on relative distance [S1601], and a ratio scale
systematizes the steps [S1637]. Not found in the sources read: a numeric
minimum ratio between within-group and between-group space.

**Also seen.** Layer actions mix a dashed ▲, an outlined ▼ and a quiet
"remove"; off (`theme.css:136-139`) and pending (`theme.css:170-174`) share the
dashed border.

### 3. Foundations: the spec

This spec turns §1 into tokens and fixes §2's problems. It keeps the action
hierarchy (RA-27 §10) and the design-led patterns (RA-27 §9.3). Contrast
ratios use the WCAG 2.2 formula.

#### 3.1 Type ramp

**Typeface.** All UI text uses one sans, `system-ui, -apple-system, "Segoe
UI", Roboto, sans-serif`: system fonts, so nothing loads. Mono is for keycaps
and board addresses only. Mixing typefaces "can obscure your information
hierarchy" [S1618], and monospace reads worse [S1629]. This reverses
`theme.css:36`, so **the maintainer decides**.

**Decided 2026-11-06: Martian Grotesk and Martian Mono** (RA-27b, Decisions
item 4), built (ADR-020, 2026-11-06 amendment):
- **Faces.** Grotesk at wght 400–600, wdth 100, for every role; Mono at wdth
  87.5, wght 400, for keycaps and board addresses; and Mono's digits and
  value signs, as "Martian Figures", for every number that changes while
  shown, since Grotesk has no tabular figures [S1700][S1701]. The sizes,
  weights and line heights above stay.
- **Stacks.** `--font-ui: "Martian Grotesk", system-ui, …`; `--font-code:
  "Martian Mono", ui-monospace, …`; `--font-value: "Martian Figures",
  var(--font-ui)`. Values add `font-feature-settings: "case"`, which centres
  − + × ± on the digits, and so does the eyebrow.
- **Rendering.** `font-display: swap`, which gives "an extremely small block
  period and an infinite swap period" [S1713]; the fallback must render the
  page, since under iOS Lockdown Mode "web fonts might not be displayed"
  [S1715]. `font-synthesis: none` stops a faked bold [S1712], and
  `antialiased` smoothing lightens light text on dark, on macOS only
  [S1709][S1707]. `font-weight` drives wght, never `font-variation-settings`
  [S1714].
- **Cost.** Martian runs 27–30% wider than macOS's system sans at one size,
  so on a phone fewer look names fit whole (measured in the tuning study).

**Root.** `html { font-size: 100% }`. Tokens change per pointer, never through
`em`. Compounding `em` caused the stray 9.39 px (§2.1).

| Role | Fine (size/line) | Coarse (size/line) | Weight | Colour | Used for |
|---|---|---|---|---|---|
| display | 1.125rem/1.5rem (18/24) | 1.25rem/1.625rem (20/26) | 600 | text-1 | the playing look's name, once per page |
| title | 0.9375rem/1.25rem (15/20) | 1.0625rem/1.375rem (17/22) | 600 | text-1 | inspector path `tide / base`, a lone layer's `base · pattern`, panel titles |
| heading | 0.8125rem/1.125rem (13/18) | 0.9375rem/1.25rem (15/20) | 600 | text-1 | block heads ("layers", the deck's "looks"), open step names |
| body | 0.8125rem/1.125rem | 0.9375rem/1.25rem | 400 | text-1 | button, tile, menu and layer labels, blackout; values (tabular, right-aligned) |
| label | 0.8125rem/1.125rem | 0.9375rem/1.25rem | 400 | text-2 | knob and field names |
| eyebrow | 0.6875rem/1rem (11/16) | 0.75rem/1rem (12/16) | 600, caps, +0.06em | text-2 | badges (IDLE CYCLE, DRAFT) |
| caption | 0.6875rem/1rem | 0.75rem/1rem | 400 | text-2 | units, hints, step chain, keys, "now 3.01" |
| field | as body | 1rem/1.25rem (16/20) | 400 | text-1 | typed values, text boxes, lists (`--fs-field`) |

**Tuned 2026-11-06 after the maintainer's polish review** ("the font sizes we're using
are a bit too big, and the padding everywhere is looking real funky"): the
sizes are a step smaller, and line heights are whole pixels. Martian's
x-height is 0.600 and its cap height 0.800, measured with canvas metrics in
Chromium on the served page, against 0.517 for Helvetica Neue and 0.519 for
Arial; one sample string sets 31% wider than in Helvetica Neue. So 14 px
Martian has the x-height of 16 px Helvetica Neue, and the first ramp (22/16/14/12
fine, 24/20/16/13 coarse) read a size too large. At 13 px the desktop body's
x-height is 7.8 px, about Helvetica Neue at 15 px; the phone body at 15 px
has 9.0 px, about iOS's 17 pt body (inference). The roles, weights and the
four sizes per pointer stay. Fields stay at 16 px under a finger (below).

- **Sizes.** The first ramp took M3's 12/16, 14/20, 16/24 and 22/28 on a fine
  pointer [S1610], and a larger base on a coarse one, as Apple's does
  [S1618]: 13, 16, 20 and 24 [S1637]. Since the 2026-11-06 tuning each is a
  step smaller for Martian (above): 11, 13, 15 and 18 on a fine pointer, 12,
  15, 17 and 20 on a coarse one. Phone fields stay at 16 px or more, whatever
  text is round them (`--fs-field`): iOS Safari zooms smaller ones
  (inference; source not found).
- **An exception to §1.2's 1.2–1.25 ratio.** The 13 → 15 step from body to
  title is 1.15×, as M3's titleSmall/titleMedium pair is (14/20, 16/24)
  [S1610]; position and space also separate title from heading.
- **Budget.** The page has 4 sizes, and each region uses at most 3: the deck
  uses display, body and caption; the inspector uses title, body and caption
  [S1525][S1600]. The deck's "looks" is a heading, body size at 600, so it
  adds no size (tuned 2026-11-06, second pass: as a caption it was fainter
  than the "all 13 ›" beside it, against A#3).
- **Headings.** They differ by weight and space, and by "the smallest
  increment necessary" in size [S1626]. A heading gets `--space-xs` (8) below.
  It gets `--space-lg` (24) above only after an open group. Closed disclosure
  rows are siblings, so they stack at `--control-h` with no gap [S1601]
  (inference). A heading is never smaller or fainter than what it heads (A#3).
- **Weights, tracking, figures.** Use 400 and 600 only [S1628]. Letterspace
  only the caps eyebrow [S1625][S1624], and delete the 6 `lowercase`
  transforms. Values, %, readouts and keys use `tabular-nums`
  [S1627][S1635].
- **Line height.** A whole-pixel line height per size (the table), so line
  boxes, rows and cards land on the pixel: 1.33 for display, 1.33 for the
  title, 1.38 for body and 1.45 for caption on a fine pointer. They stay near
  Butterick's 120–145% [S1623] and M3's 14/20 (1.43) [S1610]. Until the
  2026-11-06 tuning they were ratios (1.25 and 1.4), which gave 19.6 and
  16.8 px boxes.

#### 3.2 Spacing, grouping, layout

The scale has base 4 [S1639]. New names stop the old `--space-1…4`
(4/8/16/24) from silently changing. The `--space-*` steps:
- `2xs` = 4 px: inside a knob.
- `xs` = 8 px: siblings (tiles, region cards), heading to content.
- `sm` = 12 px: between knobs, deck rows, nesting indent, control padding,
  and a region card's inset above its first row (`--region-pad-block`).
- `md` = 16 px: region padding, phone gutter, and the wide deck's rows.
- `lg` = 24 px: between groups, above a heading after an open group.

**Tuned 2026-11-06 after the maintainer's polish review** (measured in Playwright on the
served page): space came from padding on every child, so the 12 and 24 px
steps rendered as 16 to 70 px. Now a knob has no padding, and what holds
knobs sets them 12 apart by its gap; a block has no top padding, and its
heading keeps 8 below. The wide deck's rows are 16 apart, twice the 8 between
rows of tiles. Every row of a list reaches 8 into the gutter with its fill
and pads 8 back, so its text keeps the column's edge, and a disclosure row's
content starts where its name does, its chevron hanging in the margin. A
tertiary word that starts or ends a row lines its ink up with the column's
edge (a margin of −9: 8 of padding and the 1 px border). Desktop knob pitch
went from 69 to 62 px, the desktop deck from 337 to 280 px, the phone deck
from 236 to 220 px, the phone knob from 108 to 96 px and the phone top bar
from 52 to 44 px.

**Tuned 2026-11-06 again, after the maintainer's polish review** (second pass, measured
in Playwright on the served page at 1440×900 and 390×844). The steps and
type sizes stay; these density rules change:
- **A head is its heading's line tall.** Controls on a head row (save, ⋯, ✕,
  "+ layer", a knob's ? and pin, "all 13 ›") hang past the line with negative
  block margins, on both pointers. So a heading's text is 8 above what it
  heads everywhere: before, it measured 10, 12, 13 and 18 px. The slot's
  heads (the look's, a panel's, a lone layer's) start their text 12 under the
  card's top. A phone knob's head is 20 px, not 40, so label→control is 4
  and knob→knob 12 there too (it was 14 and 22).
- **Trailing ink on one line.** A tertiary sign that ends a row is pulled
  past the column's edge until its icon box overhangs by 2 px, the margin the
  16-unit grid keeps round a glyph: −8 with a mouse and −14 under a finger.
  ⋯, ✕ and ? then end within 2.5 px of "delete" (they were 8–15 px inside).
  Under a finger a tertiary sign's fill is 28 px, centred on the sign, so it
  overhangs the edge by 8, as a row's fill does.
- **One value column.** Every number entry, and the brightness, gives its unit
  a fixed 16 px slot after the digits ("/s" at 11 px is 12.3 px), a unitless
  one too, so digits end on one x per pointer (1363 and 309; they spread
  12.3 and 13.4 px). Units sit on the digits' baseline.
- **One cue per nesting level.** The open layer is no raised card: its body
  starts where the name does (24 px in), its row keeps the selected fill,
  and its actions sit 8 under that fill (it was 4 from a specificity slip).
- **Closer parts.** A colour's parts are 4 apart (were 8 against 12 round
  them), the swatch is the body's line tall, and the pattern pick has no
  padding of its own (it sat 16 from its neighbours).
- **The deck's ⋯ opens in flow**, in a raised well under its row as the
  look's ⋯ does, its text on the column's edge; it covered and cut a knob
  label as an overlay. Its shuffle line is RA-27 §8's length (12 words); the
  timings live behind the look menu's ?.
- **Rhythm fixes.** The brightness's head and steps are 8 apart (blackout
  sat 4 above the steps); the make buttons take the tiles' columns; "·" and
  "→" in a row sit 4 from what they follow, as in a label; a phone's live
  tile pads 16 so its ● clears the name.
- **Whole pixels.** The side column is rounded down to whole pixels from the
  window's edge, and the phone canvas and editor floor are rounded too
  (`round(down, 30svh, 1px)`), so 1 px edges no longer fall on .48 or .19.
- **Icons on their grid.** Every icon is `--icon` (16 px), not 1em (11, 13
  or 15 px); the live ● is a 12 px mark everywhere, and in the list it
  follows the name so the keycaps end on the column's edge.

Add a step only when something uses it. Ring and outline widths (1–2 px) are
border widths, not spacing.

**Grouping.**
- Parents set `gap`, and children have no outer margin [S1638].
- The gap between groups is at least 2× the largest gap inside them, so the
  steps run 4 inside a knob, 12 between knobs, 24 between groups, then a
  surface edge. Proximity is relative [S1601] ("Avoid ambiguous spacing"
  [S1607]). The factor of 2 is inference (A#10).
- **Exception:** rows that differ in kind can sit closer, because their look
  already separates them [S1602]. The deck's rows are 12 apart, and the deck
  surface groups them [S1525].
- Each boundary gets one tool: space first, then a surface, then a line
  [S1525][S1630][S1607]. Lines appear only between library rows [S1561].

**Alignment.** Each region has one left text edge and one right control edge
[S1619][S1563]. A trailing column `--trail` wide holds ↺, ⋯ and switches.
`--trail` is `max(var(--control-h), 40px)`, where 40 px is the switch
(`theme.css:1170`): 40 px on desktop, 44 px on a phone. `--control-h` is 28 px
on desktop, Apple's default macOS control size, and 44 px on a phone, the iOS
default [S1622]. WCAG's 24 px is a minimum, not a target [S1374]. Since the
2026-11-06 tuning a control under a finger is drawn 40 px and answers 44 px
(`--hit`, a `::before` past its top and bottom edges, which rows at least 8
apart leave room for), the switch is 32×18 with a mouse and 40×24 under a
finger, so `--trail` is no longer used, and a typed value's well (`--entry`)
is 6.5rem with a mouse and 5.5rem under a finger, so the brightness's steps,
blackout and every knob's entry share both edges. The knob grid is
`1fr auto var(--trail)`:
- row 1: label, value, reset;
- row 2: the slider over columns 1–2;
- row 3: a caption (hint, "now") under the value.

This fixes the dots at 5 x positions, the switch that overflows its column,
and the readout covering the phone stepper (A#9).

**Layout.**
- **Fine pointer.** The canvas runs edge to edge on the page, with no chrome.
  The side column is `clamp(22rem, 32vw, 32rem)` and holds two region cards,
  deck and inspector, 8 px apart, each padded `--space-md`. The inspector
  stacks the layers list at its top, then 24 of space, then the picked item
  (path title and knobs). No card goes inside a card: borders "add clutter"
  and make "false floors" [S1525], so "resist immediately reaching for a
  border" [S1609].
- **Coarse pointer.** One column with 16 px gutters: canvas on top, inspector
  scrolling, deck pinned below. It shows one inspector level at a time
  (RA-27 §9.3 (c)).
- **Phone budget: deck ≤ 250 px at 390×844.** The space under the top bar (52)
  and canvas (253) is 539 px. The deck has four 44 px rows (now line, tiles,
  make, and the frame row with blackout at its end), 12 apart, plus 32 of
  padding: 244 px. The editor gets 295 px; today it gets 327 (the `.slot`,
  measured). The design-led study's "looks ⌕ find" row (RA-27 §9.3 (b)) does
  not fit, so ⌕ takes the tiles row's trailing slot (inference). The
  frame row is 358 px wide, so ☀ replaces the word "brightness" there
  (inference).
- **Blackout on a phone: the maintainer decides.** Taking it off its own full-width row is
  a safety tradeoff. With its own row the deck is 300 px and the editor
  239 px. Decided: the frame row (Open questions, 1).

**Nesting.** Each level gets one cue [S1619] (§1.4):
- look: display text, in the deck;
- layer: a row in the layers list, with the selected fill when picked, then
  the inspector title;
- step: a heading row that opens and closes;
- knob: a row indented 12 px.

At most two levels are open [S1524].

```
x16  layers                                            heading, 8 below
x16  tide                                              rows flat on the region
x16  ◼ sparks   sparkle                   60 %  [ ●]   switch in the trailing column
x16  ≡ base     5 steps                  100 %  [ ●]   selected fill, 600
                                 ↕ 24
x16  tide / base ▾                                 ⋯   title, 8 below
x16  opacity   ━━━━━━━━━━●━━━━━━━         100 %   ↺   label · value · reset
                                 ↕ 24
x16  noise                                         ›   closed steps stack, no gap
x16  osc                                           ⌄
x28    freq    ━━━●━━━━━━━━━━━━━━        1.20 Hz  ↺   indent 12, knobs 12 apart
                                 ↕ 24
x16  shape                                         ›   after an open group: 24 above
```

#### 3.3 Surfaces and elevation

A higher surface is lighter, with no shadows on the page
[S1613][S1621][S1610]. There are four levels [S1636].

| Level | Token | Value | Step | Used for | text-1 / text-2 |
|---|---|---|---|---|---|
| page | `--surface-page` | `#0b0b0e` | — | canvas, top bar, field wells | 16.82 / 8.19 |
| region | `--surface-region` | `#17171a` | 1.10 | deck and inspector cards, list rows | 15.31 / 7.45 |
| raised | `--surface-raised` | `#212124` | 1.11 | tiles, badges | 13.74 / 6.69 |
| overlay | `--surface-overlay` | `#2b2b2e` | 1.14 | menus, find sheet, toasts | 12.08 / 5.88 |

- **Text tiers.** Two tiers plus disabled, as Geist (1000, 900) [S1634] and M3
  (on-surface, on-surface-variant) [S1610] use; see §1.7. Captions differ from
  labels by size only. Both tiers pass 4.5:1 on every level [S1632]. Text on a
  tint is text-1 ("Don't use grey text on colored backgrounds" [S1607]).
- **`--border-strong` `#7b7b7e`** holds 3:1 on every level (4.66 / 4.24 /
  3.81 / 3.35) [S1531]. Today's `#60606a` falls to 2.58 on raised.
- **`--border-subtle`** is text-1 at 12% alpha (1.30–1.42). It is decorative
  only.
- **`--border-control`** is text-1 at 18% alpha, about 1.6:1 on the region
  (computed): a secondary button's edge, which comes up to `--border-strong`
  on hover. Added 2026-11-06 (second pass, flagged for the maintainer's decision):
  twelve 3:1 outlines made the side column read as a form. A text or sign
  button needs no 3:1 boundary, since its label identifies it (inference
  from WCAG 1.4.11's intent; not re-read). Fields, wells and the steps joined
  to them keep `--border-strong`.
- **States.** Geist uses a separate step for default, hover and active
  backgrounds [S1634]. Each state layer is text-1 at an alpha over its
  surface; the percentages are inference.
  - Rest: rows lie flat on their region. Of rows and tiles, only tiles are
    raised at rest.
  - Hover: 4% (1.07–1.12). Press: 8% (1.17–1.26).
  - Selected, `--surface-selected`: 12% (1.31–1.42); 1.25 from a hovered row
    on the region.
  - Selected + hover: the hover layer stacks on the selected one (1.54 on the
    region; text-2 4.85).
- **Two limits.** Text-2 on a selected fill over an overlay is 4.16, so menus
  mark the chosen option with ✓ and no fill. Danger text on a selected fill is
  4.71, and 4.21 with hover, so destructive row actions live under ⋯
  (inference).

#### 3.4 Colour roles

The neutrals lean only slightly blue: blue is 3 above red and green, down from
5–12. Linear's 2026 refresh moved from "a cool, blue-ish hue" toward "a warmer
gray that still feels crisp, but less saturated" [S1561], and greys can carry a
hue ("Greys don't have to be grey" [S1607]). Luminance is matched, so no ratio
moves by more than 0.08. Left to the maintainer; the page builds this warmer set (Open
questions, 3). The cool set was `#17171d` /
`#212129` / `#2b2b35`, text `#ededf2` / `#a6a6b2`, edge `#7a7a87`.

| Token | Value | Contrast |
|---|---|---|
| `--text-1` / `--text-2` | `#ededf0` / `#a7a7aa` | §3.3; 2.05 apart |
| `--accent` / `-hover` / `--on-accent` | `#d99a2b` / `#e6aa45` / `#0b0b0e` | 8.06 on page, 5.79 on overlay; on-accent 8.06 (9.55 on hover) |
| `--accent-tint` | `rgb(217 154 43/.16)` | text-1 on it 9.13–13.38. The tint is only 1.26–1.32 against its surface, so it always has a second cue: an accent edge (4.37–6.41), or ● and weight 600 on the live tile (● 4.97 on the tint over raised) |
| `--danger-fg` | `#f87171` | 7.11–5.10 |
| `--danger-fill` / `--on-danger` | `#b91c1c` / `#fff` | 6.47. The fill is only 2.76 against the region, so the label change also shows "confirming" |
| `--ok` | `#22c55e` | 8.63–6.19 |
| `--text-disabled` | `#5f5f62` | 2.22–3.09; exempt as an "inactive user interface component" [S1632] |

**One meaning per colour.** "Avoid using the same color to mean different
things" [S1620]. "If everything is contrasted, then nothing stands out"
[S1525][S1631].
- **Amber = the one action and what is live in the room.** Four things only:
  the primary button (solid), the playing look (tint, ● and 600 on its tile),
  a held cue and an armed trigger (tint with an accent edge).
- **Red = darkens, removes or failed.** Blackout, delete and remove use `-fg`.
  The confirming state and the lost banner use `-fill`. Three reds become one
  hue.
- **Green = connected and running.** It marks the health dot and word only.
- **Neutral = everything else:** on switches, chosen segments, selection for
  editing, focus, changed, idle cycle and warnings.

**Selected, on and live** (inference). Selected is what the page shows, so it
is neutral. Live is what the room shows, so it is amber. On is the normal state
of a layer, so it is neutral too, and the exception, off, carries the mark.

**Refinements to the action hierarchy** (RA-27 §10), each removing one accent
meaning (A#7):
- **On and chosen.** An on switch has a `--text-2` track (7.45 on the region)
  and a `--surface-page` thumb (8.19); off is a `--border-strong` edge and
  thumb, no fill. A chosen segment takes the Selected cue. Today both are
  amber (`theme.css:1191`, and RA-27 §10's segment knobs), and so are the save
  editor's checkboxes (`theme.css:898`).
- **Changed.** The amber dot becomes ↺ in the trailing column on a knob, and
  "· changed" plus `[[save]]` on a look.
- **Focus** is a text-1 outline [S1531], also on the slider thumb, which turns
  amber while dragged today (`theme.css:615-619`).
- **Warnings.** `--warn: var(--accent)` is deleted. A warning shows a word plus
  ▲.
- **IDLE CYCLE** is an eyebrow on raised: it is a mode, not a choice.
- **The picked layer** gets the selected fill, not amber (`theme.css:1374`).

#### 3.5 Emphasis and page hierarchy

**What wins at a glance** (inference; top and leading side first [S1619], at
most 2 big elements [S1525]):
1. the canvas;
2. the playing look's name, the only display text;
3. `save`, the only solid amber, shown only while it can act;
4. the tiles;
5. the inspector path, then the values;
6. blackout;
7. status chrome.

**Blackout** is styled at its rank. It is a secondary button in the danger
tone: body role in lowercase, `--danger-fg` text (6.47 on the region) on a
`--border-control` edge (`--border-strong` until the 2026-11-06 second pass),
with a red fill only while confirming. Carbon gives
destructive actions a "ghost danger style" [S1535]. It keeps a fixed place at
the end of the frame row (phone placement: §3.2).

| Region | Focal point | De-emphasized |
|---|---|---|
| Top bar | none. The look name leaves it, since it appeared 3 times (A#8) | health word, layout, ?, idle badge |
| Deck | look name + `[[save]]` | tiles; make buttons (secondary); fade (tertiary); blackout (danger text, secondary edge) |
| Inspector | path title | the layers list on top (picked row by the selected fill; step count and % as captions; neutral switches); labels and captions (text-2); ↺. Values stay text-1 |

**Budget per region:** at most 3 sizes, 1 solid amber, 1 big element.

**Test:** blur the page 5–10 px. The canvas, name, save and tiles must survive
[S1525].

#### 3.6 Signifiers

| State | Cue | Non-colour cue | Never |
|---|---|---|---|
| Action | primary: solid accent; secondary: 1 px `--border-control`, `--border-strong` on hover; tertiary: text-1 glyph or word in a fixed slot | pointer, state layer | text-2, which means static (RA-27 §10) |
| Tile | raised fill, `--radius-control`, no edge | swatch | an outline: outlines are verbs [S1602] |
| Row | flat on its region; hover 4% | icon, trailing control | a raised fill at rest |
| Field | page well, strong edge | tabular value; − + inside | the button look |
| Selected | `--surface-selected` | weight 600 | amber; an edge |
| On (switch, segment) | switch: `--text-2` track; segment: as Selected | thumb position; weight 600 | amber |
| Off (editable) | switch: `--border-strong` edge, no fill; content text-2 | the word "off" | opacity (it gave 2.49, §2.2) |
| Live (playing look) | `--accent-tint`, no edge | ● and weight 600 | an outline; solid amber |
| Held cue, armed trigger | `--accent-tint` with an accent edge | pressed state | solid amber |
| Changed | ↺, trailing column | "· changed" + save | a coloured dot |
| Busy | the control's fill pulses | `aria-busy`; presses ignored (RA-27 §10) | dashes; amber |
| Disabled | `--text-disabled`, no edge | reason inline (RA-27 §10) | dashes |
| Confirming | `--danger-fill` | label "again to …" | the word "armed", which names a trigger state [S1602] |
| Focus | 2 px `--focus` outline, 2 px offset | — | colour alone |

Clickable elements must look clickable [S1605]; weak signifiers cost 22% more
time [S1525]; "selected is not a button state" [S1606]; colour is never the
only cue [S1633].

#### 3.7 Before and after: A#1–A#5

**A#1. Looks, actions and steppers share one outline and a 5.2 px gap.**

```
BEFORE  [copper-tide ↻] [depth-charge ↻] [ember-fountain ↻]
        [surprise] [like this] [keep] ?          [fade: saved ▾]
AFTER   depth-charge · changed                 [[save]]  ⋯    display, caption, primary
                                ↕ 12
        ▚ copper-tide  ▚ depth-charge ●  ▚ ember-fountain  ⌕   raised tiles 8 apart; live: tint, ●, 600
                                ↕ 12
        [⚄ surprise me]  [≈ vary this]                       secondary
                                ↕ 12
        brightness ━━━━━●──── 75%   fade: own ▾   [blackout]  fade tertiary; blackout red text, grey edge
```

| # | Before | After |
|---|---|---|
| A#2 | `save…` muted, no edge, outweighed by `[fade: saved ▾]` | `[[save]]`: accent with `--on-accent` 600 (8.06), only when changed or a draft. `⋯` holds save as new… and revert. The fade choice stops saying "saved": `fade: saved` (`domain/aura/looks.ts:102`) becomes, for example, `fade: look's own` (`infra/wire/protocol.ts:142` calls it "the look's own fade"). **The maintainer picks the word**: decided `fade: as saved` (Open questions, 2) |
| A#3 | "layers · top first" 11.05 px muted 400, tracked; labels 13 px muted | "layers": heading 14/600/text-1, 8 below. "top first" becomes a caption. Labels: 14/400/text-2 |
| A#4 | 11.05 / 13 / 14.95 mono at 1.15×, a stray 9.39, bold in 6 rules | §3.1's roles. Display is 1.375× the title on desktop and 1.2× on a phone, and appears once. Weight and colour also separate the levels |
| A#5 | 12× `border-top` at 1.26:1; page and panel 1.05:1 apart | Region cards 1.10:1 off the page. Groups 24 apart, knobs 12. The picked layer gets the selected fill. Library rows keep the only divider |

#### 3.8 Tokens and migration

```css
:root {
  color-scheme: dark;
  --font-ui: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-code: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  /* tuned 2026-11-06 after the maintainer's polish review: sizes a step smaller, line heights whole pixels */
  --fs-display: 1.125rem; --fs-title: 0.9375rem; --fs-body: 0.8125rem; --fs-caption: 0.6875rem;
  --lh-display: 1.5rem; --lh-title: 1.25rem; --lh-body: 1.125rem; --lh-caption: 1rem;
  --fs-field: var(--fs-body);
  --fw-regular: 400; --fw-strong: 600;
  --track-caps: 0.06em;
  --space-2xs: 0.25rem; --space-xs: 0.5rem; --space-sm: 0.75rem;
  --space-md: 1rem; --space-lg: 1.5rem;
  --region-pad-block: var(--space-sm);
  --radius-control: 6px; --radius-inset: 8px; --radius-surface: 12px; --radius-pill: 999px;
  --surface-page: #0b0b0e; --surface-region: #17171a;
  --surface-raised: #212124; --surface-overlay: #2b2b2e;
  --state-hover: rgb(237 237 240 / 0.04); --state-press: rgb(237 237 240 / 0.08);
  --surface-selected: rgb(237 237 240 / 0.12);
  --text-1: #ededf0; --text-2: #a7a7aa; --text-disabled: #5f5f62;
  --border-strong: #7b7b7e; --border-subtle: rgb(237 237 240 / 0.12); --focus: var(--text-1);
  --border-control: rgb(237 237 240 / 0.18); /* added 2026-11-06, second pass: a secondary button's edge */
  --accent: #d99a2b; --accent-hover: #e6aa45; --on-accent: #0b0b0e;
  --accent-tint: rgb(217 154 43 / 0.16);
  --danger-fg: #f87171; --danger-fill: #b91c1c; --on-danger: #fff;
  --ok: #22c55e;
  --control-h: 28px; --hit: var(--control-h); --thumb: 12px; --slider-h: 24px;
  --icon: 16px; --entry: 6.5rem;
}
@media (pointer: coarse) {
  :root { --fs-display: 1.25rem; --fs-title: 1.0625rem; --fs-body: 0.9375rem; --fs-caption: 0.75rem;
          --lh-display: 1.625rem; --lh-title: 1.375rem; --lh-body: 1.25rem; --lh-caption: 1rem;
          --fs-field: 1rem;
          --control-h: 40px; --hit: 44px; --thumb: 20px; --slider-h: 32px; --entry: 5.5rem; }
}
html { font-size: 100%; }
body { background: var(--surface-page); color: var(--text-1);
       font: var(--fw-regular) var(--fs-body)/var(--lh-body) var(--font-ui); }
.t-display { font: var(--fw-strong) var(--fs-display)/var(--lh-display) var(--font-ui); }
.t-title   { font: var(--fw-strong) var(--fs-title)/var(--lh-title) var(--font-ui); }
.t-heading { font: var(--fw-strong) var(--fs-body)/var(--lh-body) var(--font-ui); }
.t-label   { color: var(--text-2); }
.t-value   { font-variant-numeric: tabular-nums; }
.t-eyebrow { font-size: var(--fs-caption); line-height: var(--lh-caption); font-weight: var(--fw-strong);
             color: var(--text-2); letter-spacing: var(--track-caps); text-transform: uppercase; }
.t-caption { font-size: var(--fs-caption); line-height: var(--lh-caption); color: var(--text-2); }
input, select { font-size: var(--fs-field); }
:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
```

The radius merges 6 and 8 into one value for controls, tiles and rows, since
2 px apart is not visible (inference). Since the 2026-11-06 tuning a well
nested in a region (what the look's ⋯ and the deck's ⋯ open, a stop's editor)
takes `--radius-inset` 8, so a 6 px control 8 px inside it does not echo its
corner; the colour control's well is gone, as no card goes inside a card
(§3.2), and since the second pass so is the open layer's card.

**Migration** (counts from §2.1 and a grep of `theme.css`):

| Now | Becomes |
|---|---|
| mono everywhere, plus a prose stack | `--font-ui`; `--font-code` for keys and addresses |
| 24× `var(--small)`, `1.15em`, 13/16 px root: 4 rendered sizes | 4 size tokens per pointer in 7 roles; no `em` |
| 6× `bold`, 1× `normal` | 2 weight tokens |
| 8 letter-spacings, 6 `lowercase` | 1, eyebrow only |
| 21 lengths (17 of ~110 tokenised) | 5 space steps for every margin, padding and gap |
| 10 radius values | 3 radius tokens |
| 13 hex + 4 rgba literals | role tokens; no hex outside `:root` |
| 5 opacity states | colour tokens |
| 12 `border-top` hairlines | 0 (library rows only) |
| accent in 23 declarations | 4 uses: primary, live look, held cue, armed trigger |

The 8 letter-spacing declarations hold §2.1's 4 distinct values.

**Renames:** `--bg`→`--surface-page`, `--panel`→`--surface-region`,
`--line`→`--border-subtle`, `--line-strong`→`--border-strong`,
`--muted`→`--text-2`, `--text`→`--text-1`, `--accent-soft`→`--accent-tint`,
`--danger`/`--danger-bg`→`--danger-fill`, `--danger-text`→`--danger-fg`,
`--small`→`--fs-caption`, `--space-1…4`→`2xs`/`xs`/`md`/`lg`, `--gap`→`xs`,
`--radius`→`--radius-control`, `--target`→`--control-h`. `--warn` is deleted.

Delete the old names in the same change, then grep for them and expect
nothing. An undefined `var()` fails silently (inference).

## Verdicts

These rate each source family as a reference for the page's visual
foundations, not as technology to build on. Maintenance status was not
researched.

- **Design systems** (Material 3 [S1610]–[S1617], Apple HIG
  [S1618]–[S1622], Geist [S1634][S1635][S1636][S1579], Carbon
  [S1639][S1535], Linear [S1561][S1563]): **stable**. The primary references
  for type sizes, surfaces, states and colour roles.
- **Research and typography references** (NN/g [S1600]–[S1606][S1524][S1525],
  Butterick [S1623]–[S1629], Laws of UX [S1630][S1631], Every Layout
  [S1637][S1638]): **stable**. The basis for grouping, spacing, headings and
  signifiers.
- **Refactoring UI** [S1607][S1608][S1609]: **stable**, but only its chapter
  titles, one preview chapter and one article were read, so its cites support
  rules the other sources also state.
- **WCAG 2.2** [S1632][S1633][S1531][S1374]: **stable**; the floor for
  contrast, colour and targets.

## Code-reading queue

1. **The page at the `fx-ui-polish` head.** Every line cited here is at
   8853368. Re-run §2's measurements once `fx-ui-polish` lands, before building
   on a line.
2. **Gaps:** m3.material.io's exact type sizes (not in the rendered text
   [S1615]); Refactoring UI's chapter text; a source for iOS Safari zooming
   fields under 16 px.

## Open questions

Of the four questions this study left to the maintainer, three are decided and the page
builds the fourth's working value. Do not ask them again, or change the page
back to an earlier working value:
1. **Blackout on a phone** joins the frame row (editor 295 px) or keeps
   its own row (editor 239 px)? §3.2. **Decided: the frame row**
   (RA-27b, Decisions item 7). 6c1f7b9 built the own-row layout, with
   blackout under a brightness slider that takes the row's width; phase 2
   moves it.
2. **The fade word** that replaces "saved"? §3.7, A#2. **Decided:
   `fade: as saved`**, the glossary's word (RA-27 §8, adopted in RA-27b,
   Decisions item 3), not the working value `fade: look's own`. Built:
   `web/src/domain/aura/looks.ts:206`.
3. **Warmer neutrals** (blue bias 3) or the cool set (5–12)? §3.4. **Built
   with the working value, warmer** (`web/src/ui/theme.css:67-70`). This
   choice is not in the maintainer's recorded decisions.
4. **Sans in place of mono?** §3.1. **Decided: Martian Grotesk and Martian
   Mono** (RA-27b, Decisions item 4), built per §3.1 and ADR-020's
   2026-11-06 amendment.

Not found in the sources read: a ranking of emphasis tools (§1.1); a minimum
within/between spacing ratio (A#10); an M3 statement that the primary role
covers selected states, so the selected/live split is inference (§3.4); a
source for the 250 px phone deck budget, which comes from the arithmetic in
§3.2.
