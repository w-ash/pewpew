import { Dialog } from "@ark-ui/react/dialog";
import { Portal } from "@ark-ui/react/portal";
import { useId } from "react";
import { PanelHead } from "../design/Panel";
import { useKeysOn, useShortcutList } from "../design/shortcuts";
import { Switch } from "../design/Switch";

/** Keys a control takes while it has focus, which the page registers no shortcut for. */
const ON_A_CONTROL: readonly { readonly keys: string; readonly label: string }[] = [
  { keys: "← → Home End", label: "move between the looks" },
  { keys: "Alt+↑ ↓", label: "move a layer up or down" },
  { keys: "Backspace", label: "put a knob back (live in the room)" },
];

/** The keyboard shortcuts, each as the `?` list registers it, then the keys a focused control takes. */
export function ShortcutHelp({ open, onClose }: { open: boolean; onClose(): void }) {
  const titleId = useId();
  const list = useShortcutList();
  const [keysOn, setKeysOn] = useKeysOn();
  return (
    <Dialog.Root open={open} onOpenChange={(d) => d.open || onClose()} ids={{ title: titleId }}>
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content className="shortcut-help">
            <PanelHead titleId={titleId} title="keyboard shortcuts" onClose={onClose} />
            <Switch checked={keysOn} onChange={setKeysOn}>
              single-key shortcuts
            </Switch>
            <dl>
              {[...list.map((s) => ({ keys: s.hotkey, label: s.label })), ...ON_A_CONTROL].map((s) => (
                <div key={s.keys + s.label}>
                  <dt>
                    <kbd>{s.keys}</kbd>
                  </dt>
                  <dd>{s.label}</dd>
                </div>
              ))}
            </dl>
            <p className="note">Single keys pause while you type or turn a knob. Esc always works.</p>
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  );
}
