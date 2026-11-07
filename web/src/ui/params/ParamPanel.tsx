import { Accordion } from "@ark-ui/react/accordion";
import { useId, useState } from "react";
import { settable } from "../../domain/params/kinds";
import { caption, type Param } from "../../domain/params/schema";
import { liveLook } from "../../domain/aura/looks";
import { contextOf, isMix, isSignal, mixAddress, ownerOf, pageCase, panelOf, type NodeItem, type PanelView, type Section } from "../../domain/stack/stack";
import { setParam } from "../../infra/wire/protocol";
import { useAtDefaults, useOffSaved, useParamValue, useSender, useWire } from "../../infra/wire/store";
import { Button } from "../common/Button";
import { ChangedMark } from "../common/ChangedMark";
import { DisclosureButton, DisclosureNote, useDisclosure } from "../common/Disclosure";
import { ErrorBoundary } from "../common/ErrorBoundary";
import { Icon } from "../common/Icon";
import { loadLocal, saveLocal } from "../common/local";
import { ParamField } from "./ParamField";

const CLOSED_KEY = "pewpew.closed-groups";
const OPEN_KEY = "pewpew.open-signals";

function loadList(key: string): string[] {
  try {
    const v: unknown = JSON.parse(loadLocal(key) ?? "[]");
    return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

const field = (p: Param, context?: string, owner?: string, label?: string, drives?: string) => (
  <ErrorBoundary key={`${p.name}:${p.kind}`} resetKey={p} fallback={<p className="param unknown">{caption(p)}: this page cannot show its value</p>}>
    <ParamField p={p} context={context} owner={owner} label={label} drives={drives} />
  </ErrorBoundary>
);


/** What signal section `s` drives, in words: each knob it moves by its caption, with what it belongs
 * to where another layer or node has a knob that reads alike, then each signal that reads it. */
function drivesOf(s: Section<Param>, all: readonly Param[]): readonly string[] {
  const knobs = (s.moves ?? []).map((path) => {
    const p = all.find((q) => q.name === path || path.startsWith(`${q.name}.`));
    if (!p) return path.split(".").pop()!;
    const shared = all.some((q) => q.layer && q.layer !== p.layer && caption(q) === caption(p));
    const context = contextOf(p, all, caption, shared);
    return `${caption(p).toLowerCase()}${context ? ` · ${context}` : ""}`;
  });
  return [...knobs, ...(s.feeds ?? [])];
}

/** The running look's knobs with layer `layer` picked (`panelOf`). */
export function usePanel(layer: string | null): { view: PanelView<Param>; count: number } {
  const all = useWire((s) => s.params);
  const stack = useWire((s) => s.aura?.stack ?? null);
  const count = stack?.layers.length ?? 0;
  const mixed = !useAtDefaults(all.filter((p) => count === 1 && isMix(p)));
  return { view: panelOf(all, stack, layer, mixed), count };
}

/** Sections that fold, each started open, or `shut`; the ones folded the other way are remembered on this
 * device, unless `forget`. A section's title, a heading at `level` (under a block's heading, or in a layer's
 * row), names it, then what kind of thing it is, what it reads and, for a signal, what it drives. Each knob
 * says what it belongs to, for assistive tech: its signal, or its node where another of its layer reads
 * alike, and its layer when `layered`. A macro is called by its name, as in the main knobs. */
function Sections({ sections, shut, layered, forget, level }: { sections: readonly Section<Param>[]; shut: boolean; layered?: boolean; forget?: boolean; level: 4 | 5 }) {
  const params = useWire((s) => s.params);
  const signals = useWire((s) => s.aura?.stack.signals);
  const key = shut ? OPEN_KEY : CLOSED_KEY;
  const [flipped, setFlipped] = useState(() => (forget ? [] : loadList(key)));
  if (!sections.length) return null;
  const titles = sections.map((s) => s.title);
  return (
    <Accordion.Root
      multiple
      // Each item's value goes into the ids its region is labelled by, which a space would split.
      value={titles.filter((g) => flipped.includes(g) !== !shut).map(encodeURIComponent)}
      onValueChange={(d) => {
        const open = d.value.map(decodeURIComponent);
        // Read again: another block's sections may have folded since.
        const next = [...(forget ? [] : loadList(key)).filter((g) => !titles.includes(g)), ...titles.filter((g) => open.includes(g) === shut)];
        setFlipped(next);
        if (!forget) saveLocal(key, JSON.stringify(next));
      }}
    >
      {sections.map((section) => {
        const drives = drivesOf(section, params);
        return (
          <Accordion.Item key={section.title} value={encodeURIComponent(section.title)}>
            <SectionTitle section={section} drives={drives} level={level} />
            <Accordion.ItemContent>
              {section.params.map((p) =>
                field(p, undefined, contextOf(p, params, caption, !!layered), ownKnob(p, signals) ? p.node : undefined),
              )}
            </Accordion.ItemContent>
          </Accordion.Item>
        );
      })}
    </Accordion.Root>
  );
}

/** A section's title: its name, then what kind of thing it is, what it reads and what it `drives`, and
 * "· changed" while a knob in it is off the look as saved. */
function SectionTitle({ section, drives, level }: { section: Section<Param>; drives: readonly string[]; level: 4 | 5 }) {
  const off = useOffSaved(section.params);
  const Heading = level === 4 ? "h4" : "h5";
  return (
    <Heading className="row-title">
      <Accordion.ItemTrigger>
        <Accordion.ItemIndicator>
          <Icon name="chevron" />
        </Accordion.ItemIndicator>
        <span className="section-name">{section.name.toLowerCase()}</span>
        {(section.kind || section.reads.length > 0) && (
          <span className="moves">
            {section.kind && `· ${pageCase(section.kind)}`}
            {section.reads.length > 0 && ` ${section.by} ${section.reads.join(", ")}`}
          </span>
        )}
        {drives.length > 0 && <span className="moves">→ {drives.join(", ")}</span>}
        {off && <ChangedMark />}
      </Accordion.ItemTrigger>
    </Heading>
  );
}

/** Whether `p` is the value of one of the look's own knobs (a `knob` signal). */
const ownKnob = (p: Param, signals: readonly NodeItem[] | undefined) => isSignal(p) && signals?.find((n) => n.id === p.node)?.op === "knob";

/** The look's main knobs, with no heading of their own: the knobs it lists in front, each named with
 * its owner when it comes from a step or a layer (`decay · fb · base`, `ownerOf`), unless every one has the
 * same owner, which the layers name: then the owner is for assistive tech alone. A macro (a `knob` signal) is
 * called by its name, and says what it drives. */
export function LookKnobs() {
  const { view } = usePanel(null);
  const all = useWire((s) => s.params);
  const signals = useWire((s) => s.aura?.stack.signals);
  const layers = useWire((s) => s.aura?.stack.layers) ?? [];
  if (!view.front.length) return null;
  const owners = view.front.map((p) => (ownKnob(p, signals) ? undefined : ownerOf(p, layers)));
  const shared = owners.length > 1 && owners.every((o) => o && o === owners[0]);
  const front = (p: Param) => {
    const own = ownKnob(p, signals);
    const section = own ? view.signals.find((s) => s.params.includes(p)) : undefined;
    const drives = section ? drivesOf(section, all) : [];
    return own
      ? field(p, undefined, undefined, p.node, drives.length ? `→ ${drives.join(", ")}` : undefined)
      : <FrontKnob key={p.name} p={p} context={ownerOf(p, layers)} shared={shared} />;
  };
  return <div className="look-knobs">{view.front.map(front)}</div>;
}

/** What a modulator is, for the "?" after "modulators" (RA-27 §12.3). */
const MODULATORS_ABOUT = "A modulator keeps a knob moving: a wave, the beat, the music";

/** The look's modulators, after its layers, under "modulators" and its "?": a section per modulator (an
 * LFO, a random, an audio follower, a beat), started folded, each saying its kind and what it moves; one
 * look's open sections are not another's. A macro the look shows in its main knobs is left out: it is
 * there, by its name. */
export function LookSignals() {
  const { view } = usePanel(null);
  const signals = useWire((s) => s.aura?.stack.signals);
  const look = useWire((s) => (s.aura ? (liveLook(s.aura.looks, s.aura.triggers) ?? s.aura.looks?.made ?? s.aura.pattern) : ""));
  const headId = useId();
  const about = useDisclosure();
  const shown = view.signals.filter((s) => !s.params.some((p) => ownKnob(p, signals) && view.front.includes(p)));
  if (!shown.length) return null;
  return (
    <section className="block look-signals" aria-labelledby={headId}>
      <header className="block-head">
        <h3 id={headId} className="t-heading">
          modulators
        </h3>
        <DisclosureButton disclosure={about} label="about modulators" />
      </header>
      <DisclosureNote disclosure={about}>{MODULATORS_ABOUT}</DisclosureNote>
      <Sections key={look} sections={shown} shut forget level={4} />
    </section>
  );
}

/** A front knob of a layer's: its context, or, `shared` by every main knob, its owner for assistive tech
 * alone; while its layer is switched off, its context says "(off)". */
function FrontKnob({ p, context, shared }: { p: Param; context: string | undefined; shared: boolean }) {
  const enabled = useWire((s) => s.params.find((q) => q.name === mixAddress(p.layer, "enabled")));
  const on = useParamValue(enabled ?? p);
  if (!enabled || on !== false) return shared ? field(p, undefined, context) : field(p, context);
  return field(p, `${context || p.layer} (off)`);
}

/** "reset to defaults": every knob of `knobs` back to its default, not to the look's saved value, in
 * two presses. */
export function DefaultsButton({ knobs }: { knobs: readonly Param[] }) {
  const sender = useSender();
  return (
    <Button
      variant="tertiary"
      confirm="again to reset all"
      title="every knob shown here back to its default"
      onPress={() => {
        for (const p of knobs) if (settable(p)) setParam(sender, p, p.default);
      }}
    >
      reset to defaults
    </Button>
  );
}

/** The knobs of layer `layer` of the running look, in display order: those in no section, then a
 * section per group, or per node in a program; never its mix, which its row, or a lone layer, shows itself. */
export function useLayerKnobs(layer: string): { loose: readonly Param[]; sections: readonly Section<Param>[]; all: readonly Param[] } {
  const view = usePanel(layer).view;
  const own = (p: Param) => !isMix(p);
  const loose = view.loose.filter(own);
  const sections = view.sections.map((s) => ({ ...s, params: s.params.filter(own) })).filter((s) => s.params.length);
  return { loose, sections, all: [...loose, ...sections.flatMap((s) => s.params)] };
}

/** Layer `layer`'s knobs (`useLayerKnobs`), in its open row or as the look's lone layer: its sections
 * (a program's steps) start folded to their titles unless `open`, headed at `level` (5 unless named). A
 * layer of one section shows its knobs loose: the fold would hide them for nothing. For assistive tech,
 * each knob names its layer where the look has several. */
export function LayerKnobList({ layer, open, level }: { layer: string; open?: boolean; level?: 4 | 5 }) {
  const knobs = useLayerKnobs(layer);
  const all = useWire((s) => s.params);
  const layered = useWire((s) => (s.aura?.stack.layers.length ?? 0) > 1);
  const one = !knobs.loose.length && knobs.sections.length === 1;
  return (
    <>
      {(one ? knobs.all : knobs.loose).map((p) => field(p, undefined, contextOf(p, all, caption, layered)))}
      {!one && <Sections sections={knobs.sections} shut={!open} layered={layered} level={level ?? 5} />}
    </>
  );
}
