import { Field } from "@ark-ui/react/field";
import { useEffect, useId, useRef, useState } from "react";
import { formatNumber, percent } from "../../domain/params/format";
import { defOf, formatValue, readValue, settable as canSet } from "../../domain/params/kinds";
import { caption, type Param, type ValueOf } from "../../domain/params/schema";
import type { Help } from "../../domain/stack/catalog";
import { depthOf, frontFirst, isOpacity, movedBy, pickedFront, type RouteItem, type SignalItem } from "../../domain/stack/stack";
import { setParam } from "../../infra/wire/protocol";
import { useMod, useParamRefusal, useParamValue, useSender, useWire } from "../../infra/wire/store";
import { IconButton, ToggleButton } from "../common/Button";
import { Details } from "../common/Details";
import { DisclosureButton, useDisclosure } from "../common/Disclosure";
import { spaced } from "../common/spaced";
import { sayStep } from "../common/StepStatus";
import { isTextEntry } from "../common/textEntry";
import { useDraft } from "../common/useDraft";
import { useOnChange } from "../common/useOnChange";
import { noteSet } from "./lastSet";
import { controlFor } from "./registry";

const NO_ROUTES: readonly RouteItem[] = [];
const NO_SIGNALS: readonly SignalItem[] = [];

interface Props<P extends Param> {
  readonly p: P;
  /** What a knob shown outside its section belongs to, after its label. */
  readonly context?: string | undefined;
  /** What it belongs to, for assistive tech alone: a knob in its own layer's row. */
  readonly owner?: string | undefined;
  /** What it is called, in place of its caption. */
  readonly label?: string | undefined;
  /** What it drives, in words, under it. */
  readonly drives?: string | undefined;
  /** In place of the param's help: null for none, or what its value means, shown while its "?" is
   * pressed, with more behind a disclosure. */
  readonly about?: ((value: ValueOf<P>) => Help) | null;
}

/** `v` as the control of `p` shows it: a layer's opacity and a color's levels as percents, a
 * choice in lower case. */
function shownValue<P extends Param>(p: P, v: ValueOf<P>): string {
  if (isOpacity(p) && typeof v === "number") return percent(v);
  const text = formatValue(p, v);
  return p.kind === "choice" ? text.toLowerCase() : text;
}

/** The addresses of the knobs the look shows first, as its block shows them (`panelOf`). */
function useFront(): readonly string[] {
  const stack = useWire((s) => s.aura?.stack ?? null);
  const params = useWire((s) => s.params);
  return stack ? frontFirst(params, stack.front.length ? stack.front : pickedFront(stack, params)).front.map((p) => p.name) : [];
}

/** One param: label, `context`, its kind's glance, the reset, whether the look shows it above
 * (`FrontPin`), its "?", help (or `about`), what modulates it and the live value it moves it to, control, a
 * note on a typed value it changed, and the engine's refusal. The "?" is a disclosure: it shows the help
 * and what moves the knob under its line while open, by the "?" however tall the control, until Esc or
 * another note opens; at rest a slider's live mark alone says a route moves it, unless motion is
 * reduced, when the line shows at rest (page.css). The reset (↺, or Backspace) puts back the saved
 * look's value; while the knob is off it, ↺ shows at rest, the knob's sign of changed. With no saved
 * value it puts back the default, and shows under a pointer or with focus. The "?" ends the line, so
 * showing the others never moves it (page.css). The control shows the value itself; the live value is
 * a readout only, hidden from assistive tech, which reads the line on what moves it once. The help
 * describes the control always. */
export function ParamField<P extends Param>({ p, context, owner, label, drives, about }: Props<P>) {
  const def = defOf(p);
  const sender = useSender();
  const echoed = useParamValue(p);
  const routes = useWire((s) => s.aura?.stack.routes) ?? NO_ROUTES;
  const signals = useWire((s) => s.aura?.stack.signals) ?? NO_SIGNALS;
  // A recall that waits replaces the edits: no knob is marked off a look that is going.
  const savedJson = useWire((s) => (s.aura?.looks?.pending ? undefined : s.aura?.looks?.saved?.[p.name]));
  const moved = movedBy(routes, p.name, (part, depth) => depthOf(p, part, depth), signals);
  const mod = useMod(p.name);
  const liveText = mod === null || (p.kind !== "float" && p.kind !== "int") ? null : isOpacity(p) ? percent(mod) : formatNumber(p, mod);
  const live = liveText !== null ? mod : null;
  const draft = useDraft(echoed, def.equal);
  // A refusal shows while it is the store's latest for this param and the
  // engine's value has not moved since; a change here, another tab's set or
  // a new connection ends it.
  const refusal = useParamRefusal(p.name);
  const [refused, setRefused] = useState<{ refusal: typeof refusal; echoed: ValueOf<P> } | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const asking = useDisclosure();
  const asked = asking.open;
  useOnChange(refusal, () => {
    if (!refusal) return;
    draft.drop();
    setRefused({ refusal, echoed });
  });
  const error = refused && refusal && refused.refusal === refusal && refused.echoed === echoed ? refusal.reason : null;
  const settable = canSet(p);
  const send = (v: ValueOf<P>) => {
    setRefused(null);
    setNote(null);
    draft.change(v);
    noteSet(p, echoed, v);
    setParam(sender, p, v);
  };
  const change = (raw: ValueOf<P>) => send(def.normalize(p, raw, draft.shown));
  const saved = savedJson === undefined ? undefined : readValue(p, savedJson);
  const changed = saved !== undefined && !def.equal(draft.shown, saved);
  // The saved value while it differs; with none, the default as declared, as defaults sends it: it
  // may sit between steps. "reset to defaults" is the way to a look's defaults.
  const target = saved !== undefined ? (changed ? saved : null) : def.equal(draft.shown, p.default) ? null : p.default;
  const reset = () => {
    if (target === null) return;
    send(target);
    draft.release();
  };
  const { Control, Glance } = controlFor(p);
  const id = useId();
  const labelId = `${id}label`, helpId = `${id}help`, movedId = `${id}moved`, drivesId = `${id}drives`;
  // In lower case, as every label shows, so assistive tech reads what the page shows.
  const called = (label ?? caption(p)).toLowerCase();
  const name = [called, context || owner].filter(Boolean).join(" · ");
  const told = about && asked ? about(draft.shown) : null;
  const help = about === undefined ? p.help : (told?.lead ?? "");
  const helpRef = useRef<HTMLDivElement>(null);
  const movedRef = useRef<HTMLParagraphElement>(null);
  // Asked, the help comes into view, with its "all modes" and what moves the knob when it has them: on a
  // phone it can open at the slot's bottom.
  useEffect(() => {
    if (!asked) return;
    const help = helpRef.current;
    const more = help?.nextElementSibling;
    (movedRef.current ?? (more instanceof HTMLDetailsElement ? more : help))?.scrollIntoView({ block: "nearest" });
  }, [asked]);
  const front = useFront();
  const ready = useWire((s) => !!s.aura);
  // A knob of the running look's layers or signals can be shown above, with the look's own.
  const frontable = ready && !!(p.layer || p.node);
  const ask = about === undefined ? !!p.help || !!moved : !!about;
  // A slider marks where a route moves it; another kind says so at rest.
  const marked = p.kind === "float" || p.kind === "int";
  const describers = [moved ? movedId : "", drives ? drivesId : "", help ? helpId : ""].filter(Boolean);
  const describedBy = describers.length ? describers.join(" ") : undefined;
  // What its "?" shows: the help, all modes and what moves it, as far as it has them.
  const shows = spaced(help && helpId, told?.more && `${id}more`, moved && movedId);
  return (
    <Field.Root
      className="param"
      data-kind={p.kind}
      data-param={p.name}
      invalid={error !== null}
      ids={{ label: labelId, helperText: helpId }}
      aria-labelledby={labelId}
      onKeyDown={(e) => {
        if (!settable || target === null || (e.key !== "Backspace" && e.key !== "Delete")) return;
        if (isTextEntry(e.target as Element)) return;
        e.preventDefault();
        reset();
      }}
    >
      <div className="param-head">
        <Field.Label>
          {called}
          {context && (
            <span className="context">
              <span className="sep"> · </span>
              {context}
            </span>
          )}
          {!context && owner && <span className="sr-only"> · {owner}</span>}
        </Field.Label>
        {Glance && <Glance p={p} value={draft.shown} />}
        <span className="knob-end">
          <IconButton
            icon="reset"
            className="reset"
            data-changed={changed || undefined}
            hidden={!settable || target === null}
            label={target === null ? "reset" : `${changed ? "revert" : "reset"} ${name.toLowerCase()} to ${shownValue(p, target)}`}
            title={changed ? "back to the saved look's value (Backspace)" : "reset to default (Backspace)"}
            onPress={reset}
          />
          {frontable && <FrontPin path={p.name} name={name.toLowerCase()} front={front} />}
          {ask && (
            <DisclosureButton
              disclosure={asking}
              label={`about ${name.toLowerCase()}`}
              controls={shows || helpId}
            />
          )}
        </span>
      </div>
      {help && (
        <Field.HelperText ref={helpRef} className="knob-help" hidden={!asked}>
          {help}
        </Field.HelperText>
      )}
      {told?.more && (
        <Details summary="all modes" className="knob-help note" id={`${id}more`}>
          <p>{told.more}</p>
        </Details>
      )}
      {moved && (
        <p ref={movedRef} id={movedId} className="note moved" hidden={marked && !asked}>
          {moved}
          {liveText && asked && (
            <span className="live t-value" aria-hidden="true">
              {" "}· now {liveText}
            </span>
          )}
        </p>
      )}
      <Control
        p={p}
        value={draft.shown}
        onChange={change}
        onCommit={draft.release}
        onNote={setNote}
        labelId={labelId}
        name={name}
        describedBy={describedBy}
        live={live}
      />
      {drives && (
        <p id={drivesId} className="note moved">
          {drives}
        </p>
      )}
      {note && (
        <p className="note" role="status">
          {note}
        </p>
      )}
      <Field.ErrorText>{error}</Field.ErrorText>
    </Field.Root>
  );
}

/** Whether knob `path` (`name` in words) is one of the look's main knobs, at its top, as a toggle: one
 * press adds it, two take it off, as a layer's remove does; an edit of the look, which a save keeps. Each
 * says what it did, for assistive tech. A knob taken off the main knobs hands focus to its copy in its own
 * step, when that shows. */
function FrontPin({ path, name, front }: { path: string; name: string; front: readonly string[] }) {
  const sender = useSender();
  const shown = front.includes(path);
  const fire = () => {
    sender.send({ type: "front", paths: shown ? front.filter((n) => n !== path) : [...front, path] });
    sayStep(`${name} ${shown ? "taken off" : "added to"} the main knobs`);
    if (!shown) return;
    const copies = document.querySelectorAll<HTMLElement>(`[data-param="${CSS.escape(path)}"] .pin`);
    [...copies].find((pin) => !pin.closest(".look-knobs"))?.focus();
  };
  return (
    <ToggleButton
      variant="tertiary"
      icon="pin"
      className="pin"
      pressed={shown}
      label={`${name} in the main knobs`}
      title={shown ? "a main knob (press twice to take it off)" : "add to the main knobs, at the look's top"}
      confirmOff="again to take off"
      say={`take ${name} off the main knobs? press again to confirm`}
      onPressedChange={fire}
    />
  );
}
