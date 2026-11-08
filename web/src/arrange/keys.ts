import { useShortcuts } from "../design/shortcuts";
import { remove } from "./arrangement";
import { useDoc } from "./doc";

/** The editor's keys, on the page's shortcuts (design/shortcuts.ts): undo and redo, delete what is selected,
 * and with `escape`, Esc to select nothing. The Console leaves Esc to its panels and two-press buttons. */
export function useEditorKeys(escape: boolean) {
  const undo = () => useDoc.getState().undo();
  const redo = () => useDoc.getState().redo();
  const removeSelected = () => {
    const doc = useDoc.getState();
    if (!doc.selection) return;
    doc.commit(remove(doc.history.present, doc.selection));
    doc.select(null);
  };
  const hasSelection = () => useDoc.getState().selection !== null;
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
