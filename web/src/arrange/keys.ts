import { useEffect } from "react";
import { useShortcuts } from "../design/shortcuts";
import { remove } from "./arrangement";
import { useDoc } from "./doc";

/** Whether the last press or focus was inside the editor's `scope`: one editor's keys are on at a time. */
let active = false;

/** Track whether the editor is the active area: a press or focus inside `scope`, a CSS selector, makes it
 * active, and one anywhere else ends that. A press counts as well as focus, since a button that a click
 * does not focus (Safari's) or a click on blank page moves no focus. */
function useActiveArea(scope: string | undefined): void {
  useEffect(() => {
    if (scope === undefined) return;
    const mark = (e: Event) => {
      active = e.target instanceof Element && e.target.closest(scope) !== null;
    };
    active = document.activeElement?.closest(scope) != null;
    document.addEventListener("pointerdown", mark, true);
    document.addEventListener("focusin", mark, true);
    return () => {
      document.removeEventListener("pointerdown", mark, true);
      document.removeEventListener("focusin", mark, true);
      active = false;
    };
  }, [scope]);
}

/** The editor's keys, on the page's shortcuts (design/shortcuts.ts): undo and redo, delete what is selected,
 * and with `escape`, Esc to select nothing. The Console leaves Esc to its panels and two-press buttons.
 * With `scope`, a CSS selector, Delete and Backspace act only while the editor is the active area: the
 * last press or focus was inside an element it matches. On the Console, a press on a deck button or on
 * blank page never deletes from the live rig. */
export function useEditorKeys(escape: boolean, scope?: string) {
  useActiveArea(scope);
  const undo = () => useDoc.getState().undo();
  const redo = () => useDoc.getState().redo();
  const removeSelected = () => {
    const doc = useDoc.getState();
    if (!doc.selection || doc.readOnly) return;
    doc.commit(remove(doc.history.present, doc.selection));
    doc.select(null);
  };
  const hasSelection = () => useDoc.getState().selection !== null && (scope === undefined || active);
  useShortcuts([
    { hotkey: "mod+z", label: "undo", action: undo },
    { hotkey: "mod+shift+z", label: "redo", action: redo },
    { hotkey: "mod+y", label: "", action: redo },
    { hotkey: "Delete", label: "delete what is selected", action: removeSelected, enabled: hasSelection },
    { hotkey: "Backspace", label: "", action: removeSelected, enabled: hasSelection },
    ...(escape
      ? [{ hotkey: "Escape", label: "select nothing", keys: "Esc", action: () => useDoc.getState().select(null) }]
      : []),
  ]);
}
