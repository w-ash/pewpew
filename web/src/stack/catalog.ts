// What a page adds a layer from: the `catalog` message (pewpew.fx.catalog.page), a card for each
// op that draws, and what each blend mode does.

/** A program a card adds: its builder chain, the program in the looks file's form, and the map
 * dimensions it runs on (those each of its ops takes). */
export interface Example {
  readonly py: string;
  readonly json: Readonly<Record<string, unknown>>;
  readonly dims: readonly number[];
}

export interface Card {
  readonly kind: "op";
  readonly name: string;
  readonly label: string;
  /** One sentence, an arg's name in backticks (`summaryText` shows it plain). */
  readonly summary: string;
  /** The op's signature (`source`, `coord`, `color`, `combine`, `modulate`). */
  readonly sig: string;
  /** The map dimensions the op runs on. */
  readonly dims: readonly number[];
  /** What to use on a map the op does not run on, or "". */
  readonly fix: string;
  /** The programs it adds, the first the card's own. */
  readonly examples: readonly Example[];
}

export interface BlendNote {
  readonly name: string;
  readonly label: string;
  readonly doc: string;
  /** Over nothing (black) it shows black: on the bottom layer it hides the layer. */
  readonly black: boolean;
}

export interface Catalog {
  readonly cards: readonly Card[];
  readonly blends: readonly BlendNote[];
}

/** The catalog's shelves, in the order a page lists them: what runs as it is (the sources a
 * layer is drawn from, each with its own color, and the effects on the layers below, each op whose
 * example reads them); then the parts a new layer is built from, by what they do. Two fields an op
 * combines are its own; the layer stack's blend modes are another thing. */
export const SHELVES = ["sources", "effects on the layers below", "space", "color", "trails and glow", "combine two patterns"] as const;
export type Shelf = (typeof SHELVES)[number];

/** The first shelf of the parts a new layer is built from. */
export const PARTS_SHELF: Shelf = "space";

const BY_SIG: Readonly<Record<string, Shelf>> = { source: "sources", coord: "space", color: "color", state: "trails and glow" };

/** Ops that mean something only inside a program: the layers below as they are, and the layer's own
 * last frame. The page edits no program, so they are no card. */
const PLUMBING = new Set(["below", "prev"]);

/** A card on a shelf, and the example its press adds. */
export interface Shelved {
  readonly card: Card;
  /** The index in `card.examples` of the one a press adds. */
  readonly at: number;
}

/** What each shelf holds of `cards`, each card on one: an op with an example that reads the layers
 * below on "effects on the layers below", with that example; any other op on its signature's shelf,
 * with its own. */
export function shelve(cards: readonly Card[]): ReadonlyMap<Shelf, readonly Shelved[]> {
  const out = new Map<Shelf, Shelved[]>(SHELVES.map((s) => [s, []]));
  for (const card of cards) {
    if (PLUMBING.has(card.name)) continue;
    const at = card.examples.findIndex((e) => readsBelow(e.json));
    if (at >= 0) out.get("effects on the layers below")!.push({ card, at });
    else out.get(BY_SIG[card.sig] ?? "combine two patterns")!.push({ card, at: 0 });
  }
  return out;
}

/** Whether `takes`, a list of map dimensions, holds a map of `dims` dimensions (the stack's: 0 to 3).
 * As the engine counts them, a point runs what a strip runs. */
function holds(takes: readonly number[], dims: number): boolean {
  return takes.includes(Math.max(dims, 1));
}

const needs = (takes: readonly number[]) => `needs a map of ${takes.join(" or ")} dimensions`;

/** Whether a map of `dims` dimensions runs `example`. */
export function fits(example: Example, dims: number): boolean {
  return holds(example.dims, dims);
}

/** Why a map of `dims` dimensions cannot run `card`'s own example, or null when it can: the op's own
 * reason first, with what to use instead. */
export function offReason(card: Card, dims: number): string | null {
  if (!holds(card.dims, dims)) return card.fix || needs(card.dims);
  const own = card.examples[0];
  return !own || fits(own, dims) ? null : `its example ${needs(own.dims)}`;
}

/** `card`'s summary as the page shows it, without its full stop: an arg's name stays in backticks,
 * for `argParts`. */
export function summaryText(card: Card): string {
  return card.summary.replace(/\.$/, "");
}

/** The gist of `card`'s summary, for its line under the label: up to its first colon or
 * semicolon. */
export function shortText(card: Card): string {
  return summaryText(card).split(/[:;] /)[0]!;
}

/** `text` in parts, every other one an arg's name (in backticks in the catalog's summaries). */
export function argParts(text: string): readonly string[] {
  return text.split("`");
}

/** The label of each source op among `cards`, by op. */
export function sourceLabels(cards: readonly Card[]): ReadonlyMap<string, string> {
  return new Map(cards.filter((c) => c.sig === "source").map((c) => [c.name, c.label]));
}

/** What a press of `card` brings besides its own op: the labels of the sources (`sources`, by op)
 * its example at `at` starts from; none for a source or an effect on the layers below. */
export function brings(card: Card, at: number, sources: ReadonlyMap<string, string>): readonly string[] {
  const json = card.examples[at]?.json;
  if (card.sig === "source" || !json || readsBelow(json)) return [];
  const nodes = json.nodes;
  if (typeof nodes !== "object" || nodes === null) return [];
  const ops = Object.values(nodes).map((n: unknown) => {
    const op = (n as { op?: unknown } | null)?.op;
    return typeof op === "string" ? op : "";
  });
  return [...new Set(ops.filter((op) => op !== card.name && sources.has(op)))].map((op) => sources.get(op)!);
}

/** What each source a card can bring makes, in the words its knobs' help uses. */
const MAKES: Readonly<Record<string, string>> = { Oscillator: "stripes", Noise: "noise hills", Lissajous: "looping knot" };

/** What a press of a card that brings the sources labelled `brought` (`brings`) adds before its own
 * op acts: `new stripes`. */
export function newText(brought: readonly string[]): string {
  return `new ${brought.map((label) => MAKES[label] ?? label.toLowerCase()).join(" and ")}`;
}

/** Whether program `json` reads the layers under it (a `below` node): an effect on them. */
export function readsBelow(json: Example["json"]): boolean {
  const nodes = json.nodes;
  return typeof nodes === "object" && nodes !== null && Object.values(nodes).some((n: unknown) => (n as { op?: unknown })?.op === "below");
}

/** The layer an `add_layer` request sends for `example`, over the running layers: screened in at
 * 0.7, so what is under it still shows; a program that reads what is under it replaces it,
 * normal at 1 (the looks file's defaults). The engine gives it its id. */
export function newLayer(example: Example): Readonly<Record<string, unknown>> {
  return readsBelow(example.json) ? example.json : { ...example.json, blend: "screen", opacity: 0.7 };
}

/** Help in two parts: what shows when asked (`lead`), and what more waits behind "all modes" (`more`). */
export interface Help {
  readonly lead: string;
  readonly more: string;
}

/** What a layer's blend "?" tells, since a list cannot say what its options do: what `mode` does, and on
 * the bottom layer when it shows black there; then what each other mode does, a line each. */
export function blendsAbout(blends: readonly BlendNote[], mode: string, bottom: boolean): Help {
  const line = (b: BlendNote) => `${b.label.toLowerCase()}: ${b.doc}`;
  const chosen = blends.find((b) => b.name === mode);
  const lead = [chosen ? line(chosen) : mode, ...(bottom && showsBlack(blends, mode) ? [`Nothing is below this layer, so ${mode} shows black.`] : [])];
  return { lead: lead.join("\n"), more: blends.filter((b) => b !== chosen).map(line).join("\n") };
}

/** Whether blend mode `mode` shows black over nothing. */
export function showsBlack(blends: readonly BlendNote[], mode: string): boolean {
  return blends.find((b) => b.name === mode)?.black ?? false;
}
