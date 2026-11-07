// What a press does, shared by every pressable component: one press acts, or a confirm takes two; a
// reason turns presses into its note; busy turns them off; a key can press it.
import { useEffect, useImperativeHandle, useRef, type MouseEvent, type Ref, type RefObject } from "react";
import type { Disclosure } from "./Disclosure";
import { pressable, useShortcuts } from "./shortcuts";
import { sayArmed, useArm, useArmedLine } from "./useArm";
import { useOnChange } from "./useOnChange";

export interface PressOptions {
  /** What a first press shows, from "again to …" ("again to delete"): a second press within a few
   * seconds acts. Absent: one press acts. */
  readonly confirm?: string | undefined;
  /** Whether this press needs the second; false acts at once. A button that sometimes confirms names its
   * `confirm` always, so it is as wide either way. */
  readonly twoPress?: boolean | undefined;
  /** What the arm status says while confirming, in place of "press <confirm>". */
  readonly say?: string | undefined;
  /** What `note` says while confirming: what the second press costs. It replaces the arm status. */
  readonly cost?: string | undefined;
  /** Disarm when this changes: the state it acts on moved, or a refusal came. */
  readonly disarmOn?: unknown;
  /** A key that presses it while it can be pressed, and its line in the `?` list. */
  readonly shortcut?: { readonly hotkey: string; readonly label: string } | undefined;
  /** Waiting on the engine: presses do nothing. */
  readonly busy?: boolean | undefined;
  /** Why it is off now, or null: a press opens this in `note` instead of acting. */
  readonly reason?: string | null | undefined;
  /** Where a press shows `reason`, and a first press `cost`. */
  readonly note?: Disclosure | undefined;
}

/** `props` as its press options and the rest, which go to the element. */
export function splitPress<P extends PressOptions>(props: P) {
  const { confirm, twoPress, say, cost, disarmOn, shortcut, busy, reason, note, ...rest } = props;
  const options: PressOptions = { confirm, twoPress, say, cost, disarmOn, shortcut, busy, reason, note };
  return [options, rest] as const;
}

/** What a press acts with: the click, which a key's press gives as `detail` 0; none from a shortcut. */
export type Act = (click?: MouseEvent<HTMLButtonElement>) => void;

export interface Press {
  /** The button's own ref; `usePress` hands its element to the ref the button was given. */
  readonly button: RefObject<HTMLButtonElement | null>;
  /** A first press of a confirm waits for its second. */
  readonly armed: boolean;
  press: Act;
}

/** The press of a button given `ref`, which calls `act` as `options` say. */
export function usePress(act: Act, options: PressOptions, ref: Ref<HTMLButtonElement> | undefined): Press {
  const { confirm, say, cost, disarmOn, shortcut, busy, reason, note } = options;
  const twoPress = options.twoPress ?? true;
  const button = useRef<HTMLButtonElement>(null);
  useImperativeHandle(ref, () => button.current as HTMLButtonElement, []);
  const arm = useArm();
  const was = useRef(false);
  useOnChange(disarmOn, arm.disarm);
  const line = cost !== undefined ? "" : (say ?? (confirm ? `press ${confirm}` : ""));
  // The cost a first press opened in the note. Its disarm closes the note only while it still shows that
  // cost: the press that disarmed it may have armed another, whose cost is there now.
  const opened = useRef("");
  useEffect(() => {
    if (arm.armed === was.current) return;
    was.current = arm.armed;
    if (cost !== undefined) {
      if (arm.armed) {
        opened.current = cost;
        note?.show(cost);
      } else note?.close(opened.current);
    }
    if (line) sayArmed(line, arm.armed);
  }, [arm.armed, cost, note, line]);
  // The reason a press last opened in the note: it goes once the reason does, or changes.
  const told = useRef<string | null>(null);
  useEffect(() => {
    if (told.current === null || told.current === reason) return;
    note?.close(told.current);
    told.current = null;
  }, [reason, note]);
  const press: Act = (click) => {
    if (busy) return;
    if (reason) {
      told.current = reason;
      return note?.toggle(reason);
    }
    if (!confirm || !twoPress) return act(click);
    arm.press(() => act(click));
  };
  useShortcuts(shortcut ? [{ ...shortcut, action: () => press(), enabled: () => pressable(button.current) }] : []);
  return { button, armed: arm.armed, press };
}

/** The page's one polite status for confirms: what the one armed last does on a second press. */
export function ArmStatus() {
  const line = useArmedLine();
  return (
    <p className="sr-only" role="status">
      {line}
    </p>
  );
}
