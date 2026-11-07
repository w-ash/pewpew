// Keyboard shortcuts. Each component registers its own; the `?` list reads
// them back. A key on a param, a list, in a dialog or in or on an element
// marked `data-own-keys` (a form that takes a typed name, and its opener while
// it is open) belongs to it, not to the page, and the single-key shortcuts can
// be turned off (WCAG 2.1.4). Esc is not a character key: it stays on.
import { useHotkeys, useHotkeyRegistrations } from "@ark-ui/react/hotkeys";
import { useSyncExternalStore } from "react";
import { loadLocal, saveLocal } from "./deviceStorage";
import { isTextEntry } from "./textEntry";

export interface Shortcut {
  readonly hotkey: string;
  readonly label: string;
  action(): void;
  /** Checked on each press: a shortcut that presses a control is on only while the control can be pressed. */
  readonly enabled?: () => boolean;
  /** The keys as the `?` list shows them, when not `hotkey`; an empty label leaves it out. */
  readonly keys?: string;
}

// An open dialog ignores a handled Escape, so a shortcut on Esc (however the
// hotkey spells it) leaves the key for it to close on too.
const ESCAPE = /(^|\+)esc(ape)?$/i;

const OFF_KEY = "pewpew.keys-off";
const listeners = new Set<() => void>();
let keysOn = loadLocal(OFF_KEY) === null;

/** Whether the single-key shortcuts are on, kept on this device. */
export function useKeysOn(): [boolean, (on: boolean) => void] {
  const on = useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => keysOn,
  );
  const set = (next: boolean) => {
    keysOn = next;
    saveLocal(OFF_KEY, next ? null : "1");
    for (const l of listeners) l();
  };
  return [on, set];
}

function active(hotkey: string): boolean {
  const el = document.activeElement;
  if (isTextEntry(el)) return false;
  return ESCAPE.test(hotkey) || (keysOn && !el?.closest(".param, select, [role=dialog], [data-own-keys]"));
}

/** Whether a press on `el` would reach it: shown, enabled and not inert. */
export function pressable(el: HTMLElement | null): boolean {
  return !!el?.checkVisibility() && !el.closest("[inert]") && !(el instanceof HTMLButtonElement && el.disabled);
}

export function useShortcuts(list: readonly Shortcut[]): void {
  useHotkeys({
    commands: list.map((s) => ({
      hotkey: s.hotkey,
      label: s.label,
      action: () => s.action(),
      enabled: () => active(s.hotkey) && (s.enabled?.() ?? true),
      description: s.keys,
      options: { preventDefault: !ESCAPE.test(s.hotkey), enableOnFormTags: true },
    })),
  });
}

export interface ShortcutEntry {
  readonly hotkey: string;
  readonly label: string;
}

export function useShortcutList(): ShortcutEntry[] {
  return useHotkeyRegistrations().flatMap((c) => (c.label ? [{ hotkey: c.description ?? c.hotkey, label: c.label }] : []));
}
