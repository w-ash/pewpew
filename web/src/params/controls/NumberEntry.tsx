// Typed entry with ± buttons: the way to set a number without dragging. A
// typed value is sent on Enter or blur, and Esc drops it; a step or an arrow
// key is sent at once. Typing parses in the reader's locale, and a typed
// value the param cannot hold says what it became.
import { NumberInput } from "@ark-ui/react/number-input";
import { useEffect, useId, useRef, useState, type CSSProperties, type MouseEvent, type PointerEvent } from "react";
import { formatNumber, LOCALE, numberFormatOptions, numberSuffix, numberText, percentOf, typedNote } from "../format";
import { rounded, stepOff, type NumberSpec } from "../schema";
import { sayStep } from "../../design/StepStatus";

interface Props {
  readonly spec: NumberSpec;
  readonly value: number;
  readonly label: string;
  /** The ids of what describes the value, or undefined. */
  readonly describedBy?: string | undefined;
  /** Typed and shown as a percent: for a 0..1 level with no unit (`percentOf`). */
  readonly percent?: boolean;
  onChange(v: number): void;
  onCommit(): void;
  /** What became of a typed value it could not take as typed, or null. */
  onNote(note: string | null): void;
}

const STEP_KEYS = new Set(["ArrowUp", "ArrowDown", "Home", "End"]);
/** What a typed number is made of, in any locale: the entry turns away anything else unseen. */
const NUMERIC = /^[\d.,+\-\u2212eE ]*$/;

/** The value and its unit share one box, as the master's do; the boxes are as wide, so every entry
 * of a panel ends at one edge. − and + step on the param's grid: from a value between steps, to
 * the nearest step that way. A touch steps on a tap alone, as a click: a swipe that starts on one
 * scrolls and steps nothing, and a finger that rests does not repeat. A click with no press before
 * it (assistive tech's) steps too, and either says where it left the value (`sayStep`): focus stays on
 * the button, whose name does not change. */
export function NumberEntry({ spec: own, value: raw, label, describedBy, percent, onChange: set, onCommit, onNote }: Props) {
  const pct = percent ? percentOf(own) : null;
  const spec = pct ?? own;
  const value = pct ? rounded(raw * 100, 9) : raw;
  const onChange = (n: number) => set(pct ? n / 100 : n);
  // Its own id: a color field holds three entries, which must not share the field's.
  const inputId = useId();
  const input = useRef<HTMLInputElement>(null);
  // Set by an edit to the text, cleared by a step key. Native listeners: they
  // run before the input's own handlers turn the event into a value change.
  // Chromium sends Enter as a line break after the commit: not an edit.
  const typing = useRef(false);
  const [typed, setTyped] = useState<{ readonly text: string; readonly n: number } | null>(null);
  useEffect(() => {
    const el = input.current;
    if (!el) return;
    // A typed letter the entry turns away says so, rather than nothing: from its key, or on a
    // phone's keyboard, which names no key, from the text it would insert.
    const refuse = (text: string | null) => {
      if (text && !NUMERIC.test(text)) onNote(`‘${text}’ is not a number`);
    };
    const edit = (e: InputEvent) => {
      if (e.inputType === "insertLineBreak") return;
      typing.current = true;
      refuse(e.data);
    };
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape" && typing.current) {
        e.stopPropagation();
        typing.current = false;
        setTyped(null);
        onNote(null);
        return;
      }
      if (STEP_KEYS.has(e.key)) typing.current = false;
      if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) refuse(e.key);
    };
    el.addEventListener("beforeinput", edit);
    el.addEventListener("keydown", key, true);
    return () => {
      el.removeEventListener("beforeinput", edit);
      el.removeEventListener("keydown", key, true);
    };
  }, [onNote]);
  const send = (n: number) => {
    if (!Number.isFinite(n)) return;
    onChange(n);
    onCommit();
  };
  // Zag steps on a mouse's or a pen's press, and repeats while it is held. A touch's press is the
  // entry's to take: it steps on the click. So does a click no press came before: a key's, or one
  // that assistive tech sends.
  const pressedBy = useRef<string | null>(null);
  const tap = (dir: number) => ({
    onPointerDownCapture: (e: PointerEvent) => {
      pressedBy.current = e.pointerType;
      if (e.pointerType === "touch") e.stopPropagation();
    },
    onClick: (e: MouseEvent) => {
      const by = pressedBy.current;
      pressedBy.current = null;
      if (by !== null && by !== "touch" && e.detail !== 0) return;
      const n = stepOff(spec, value, dir);
      send(n);
      sayStep(`${label} ${formatNumber(spec, n)}`);
    },
  });
  const suffix = numberSuffix(spec, value);
  const digits = Math.max(numberText(spec, spec.lo).length, numberText(spec, spec.hi).length);
  return (
    <NumberInput.Root
      className="number-entry"
      ids={{ input: inputId }}
      locale={LOCALE}
      value={typed?.text ?? numberText(spec, value)}
      min={spec.lo}
      max={spec.hi}
      // A periodic value steps past its ends; the param's kind wraps it.
      allowOverflow={spec.periodic}
      step={spec.step}
      inputMode="decimal"
      focusInputOnChange={false}
      formatOptions={numberFormatOptions(spec.decimals)}
      onValueChange={(d) => {
        if (typing.current) {
          setTyped({ text: d.value, n: d.valueAsNumber });
          return;
        }
        setTyped(null);
        const n = d.valueAsNumber;
        const by = n - value;
        send(Math.abs(Math.abs(by) - spec.step) < spec.step * 1e-6 ? stepOff(spec, value, Math.sign(by)) : n);
      }}
      onValueCommit={(d) => {
        // Only text the entry took is sent: a commit of what it already showed sends nothing.
        if (typing.current && typed) {
          send(d.valueAsNumber);
          onNote(typedNote(spec, typed.text, typed.n));
        }
        typing.current = false;
        setTyped(null);
      }}
    >
      <NumberInput.Control aria-label={label}>
        <NumberInput.DecrementTrigger aria-label={`decrease ${label}`} {...tap(-1)}>
          −
        </NumberInput.DecrementTrigger>
        <span className="value-box" style={{ "--digits": digits } as CSSProperties}>
          <NumberInput.Input ref={input} className="t-value" aria-label={label} aria-describedby={describedBy} />
          <span className="unit">{suffix}</span>
        </span>
        <NumberInput.IncrementTrigger aria-label={`increase ${label}`} {...tap(1)}>
          +
        </NumberInput.IncrementTrigger>
      </NumberInput.Control>
    </NumberInput.Root>
  );
}
