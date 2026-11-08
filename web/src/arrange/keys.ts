import { useShortcuts } from "../design/shortcuts";
import { remove } from "./arrangement";
import { useDoc } from "./doc";

/** Whether focus is on the page itself or inside an element `scope` matches. */
function focusIn(scope: string): boolean {
  const el = document.activeElement;
  return !el || el === document.body || !!el.closest(scope);
}

/** The editor's keys, on the page's shortcuts (design/shortcuts.ts): undo and redo, delete what is selected,
 * and with `escape`, Esc to select nothing. The Console leaves Esc to its panels and two-press buttons.
 * With `scope`, a CSS selector, Delete and Backspace act only while focus is on the page or inside an
 * element it matches: on the Console, a deck button that has focus never deletes from the live rig. */
export function useEditorKeys(escape: boolean, scope?: string) {
  const undo = () => useDoc.getState().undo();
  const redo = () => useDoc.getState().redo();
  const removeSelected = () => {
    const doc = useDoc.getState();
    if (!doc.selection) return;
    doc.commit(remove(doc.history.present, doc.selection));
    doc.select(null);
  };
  const hasSelection = () => useDoc.getState().selection !== null && (scope === undefined || focusIn(scope));
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
