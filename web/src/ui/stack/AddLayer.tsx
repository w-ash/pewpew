import { Accordion } from "@ark-ui/react/accordion";
import { useEffect, useId, useRef, useState } from "react";
import { argParts, brings, fits, newLayer, newText, offReason, PARTS_SHELF, shelve, shortText, sourceLabels, type Card, type Example } from "../../domain/stack/catalog";
import { holdReason } from "../../domain/aura/looks";
import { useLayers, useRefusal, useSender, useWire, type Refusal } from "../../infra/wire/store";
import { Icon } from "../common/Icon";
import { Panel } from "../common/Panel";
import { useOnChange } from "../common/useOnChange";

/** What a layer can run, as cards on shelves in two groups, each named for what a press adds: under
 * "ready to play" the patterns, open, the sources and the effects on the layers below; then, under "new
 * layer from parts (advanced)", the ops by what they do, each card led by what a press adds first when its
 * example brings a source. A card adds its example right above layer `above`, the one picked, as the title
 * says, or on top when that is the top one. An add waits for its layer to run, which then `onAdded`
 * names, or for the engine's refusal, shown here; meanwhile the cards take no other press. While a cue
 * holds a look the cards wait, inert, and say why, as the editor does: an add would end the hold early. */
export function AddLayerPanel({ above, onClose, onAdded }: { above: string | null; onClose(): void; onAdded(id: string): void }) {
  const catalog = useWire((s) => s.catalog);
  const dims = useWire((s) => s.aura?.stack.dims ?? 3);
  const held = holdReason(useWire((s) => s.aura?.triggers ?? null), "add a layer");
  const ids = useLayers().map((l) => l.id);
  const sender = useSender();
  const first = useRef<HTMLButtonElement>(null);
  const [pending, setPending] = useState<{ readonly key: string; readonly ids: readonly string[] } | null>(null);
  // Set at once, so a second press before the page draws the pending card sends nothing.
  const adding = useRef(false);
  const [refused, setRefused] = useState<Refusal | null>(null);
  const refusal = useRefusal("add_layer");
  useOnChange(refusal, () => {
    adding.current = false;
    setPending(null);
    setRefused(refusal);
  });
  const added = pending ? ids.find((id) => !pending.ids.includes(id)) : undefined;
  useEffect(() => {
    if (added) onAdded(added);
  }, [added, onAdded]);
  useEffect(() => first.current?.focus({ preventScroll: true }), []);
  // Under the layer over the picked one; on top when it is the top one, or none is picked.
  const at = above === null ? -1 : ids.indexOf(above);
  const below = at < 0 ? null : (ids[at + 1] ?? null);
  const add = (key: string, example: Example) => {
    if (adding.current) return;
    adding.current = true;
    setRefused(null);
    setPending({ key, ids });
    sender.send({ type: "add_layer", layer: newLayer(example), below });
  };
  const cards = catalog?.cards ?? [];
  const sources = sourceLabels(cards);
  const shelves = [...shelve(cards)].map(([shelf, held]) => ({ shelf, held })).filter((s) => s.held.length);
  return (
    <Panel title={below === null ? "add layer" : `add above ${above}`} onClose={onClose}>
      {refused && (
        <p className="refusal" role="alert">
          {refused.reason}
        </p>
      )}
      {!catalog && <p className="note">no catalog from the aura yet</p>}
      {held && (
        <p className="note held-note" role="status" tabIndex={-1}>
          {held}
        </p>
      )}
      <Accordion.Root className="shelves" inert={!!held} collapsible lazyMount unmountOnExit defaultValue={["patterns"]}>
        {shelves.map(({ shelf, held }, i) => [
          i === 0 && (
            <h3 key="ready" className="group-head t-heading">
              ready to play
            </h3>
          ),
          shelf === PARTS_SHELF && (
            <h3 key="parts" className="group-head t-heading">
              new layer from parts (advanced)
            </h3>
          ),
          // Its value goes into the ids its region is labelled by, which a space would split.
          <Accordion.Item key={shelf} value={encodeURIComponent(shelf)}>
            <Accordion.ItemTrigger ref={i === 0 ? first : undefined}>
              <Accordion.ItemIndicator>
                <Icon name="chevron" />
              </Accordion.ItemIndicator>
              {shelf}
            </Accordion.ItemTrigger>
            <Accordion.ItemContent>
              <ul className="cards">
                {held.map(({ card, at }) => (
                  <CardItem
                    key={`${card.kind}/${card.name}/${at}`}
                    card={card}
                    at={at}
                    brings={brings(card, at, sources)}
                    dims={dims}
                    pending={pending?.key ?? null}
                    busy={pending !== null}
                    onAdd={add}
                  />
                ))}
              </ul>
            </Accordion.ItemContent>
          </Accordion.Item>,
        ])}
      </Accordion.Root>
    </Panel>
  );
}

/** `text`, an arg's name in it (in backticks) set as a token. */
function Gist({ text }: { text: string }) {
  return (
    <>
      {argParts(text).map((part, i) => (i % 2 ? <code key={i} className="arg">{part}</code> : part))}
    </>
  );
}

interface CardProps {
  readonly card: Card;
  /** The index of the example a press adds. */
  readonly at: number;
  /** The labels of the sources that example brings besides the card's op. */
  readonly brings: readonly string[];
  /** The running stack's map dimensions. */
  readonly dims: number;
  /** The key of the example an add waits on, or null. */
  readonly pending: string | null;
  /** Whether an add waits: no card takes a press meanwhile. */
  readonly busy: boolean;
  onAdd(key: string, example: Example): void;
}

/** `text`, its first letter in lower case after what a card brings (`new stripes → mirrors…`). */
const lead = (text: string, after: boolean) => (after ? text.charAt(0).toLowerCase() + text.slice(1) : text);

/** A card: one button, a row with its label (a pattern's in lower case, its file's name in its tooltip) and
 * under it its gist, led by what a press adds first when it
 * brings sources (`new stripes → mirrors one side of a pattern onto the other`), or why the map cannot
 * run it. The gist is the summary's first clause: what the rest says of how it works is for the docs. */
function CardItem({ card, at, brings: bringing, dims, pending, busy, onAdd }: CardProps) {
  const id = useId();
  const example = card.examples[at];
  const key = `${card.kind}/${card.name}/${at}`;
  if (!example) return null;
  const off = at === 0 ? offReason(card, dims) : fits(example, dims) ? null : offReason(card, dims) ?? "its example needs another map";
  return (
    <li className="card" data-off={off !== null || undefined}>
      <button
        type="button"
        className="card-add"
        aria-labelledby={`${id}name`}
        aria-describedby={`${id}gist`}
        title={card.kind === "pattern" && card.label.toLowerCase() !== card.name ? card.name : undefined}
        disabled={off !== null}
        aria-disabled={(busy && off === null) || undefined}
        data-busy={pending === key || undefined}
        aria-busy={pending === key || undefined}
        onClick={() => onAdd(key, example)}
      >
        <span id={`${id}name`} className="card-name">
          <span className="plus" aria-hidden="true">
            +{" "}
          </span>
          {card.kind === "pattern" ? card.label.toLowerCase() : card.label}
        </span>
        <span id={`${id}gist`} className="note gist">
          {off ?? (
            <>
              {bringing.length > 0 && <span>{newText(bringing)} → </span>}
              <Gist text={lead(shortText(card), bringing.length > 0)} />
            </>
          )}
        </span>
      </button>
    </li>
  );
}
