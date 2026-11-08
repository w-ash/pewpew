import { useState } from "react";
import { Button } from "../design/Button";
import { useWireContext } from "../wire/store";
import { askExport, download } from "./exporting";

/** "Export looks": every saved look, downloaded as a looks file (`looks.json`) that a run or the Console
 * opens. A refused export shows its reason here. Shown on a run that exports (capability "export"). */
export default function ExportLooks() {
  const wire = useWireContext();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const press = async () => {
    setBusy(true);
    setError(null);
    const answer = await askExport(wire, null, false);
    setBusy(false);
    if (typeof answer === "string") setError(answer);
    else download("looks.json", answer.file);
  };
  return (
    <div className="fields">
      <Button variant="secondary" busy={busy} onPress={() => void press()} title="download every saved look as a looks file">
        export looks
      </Button>
      {error && (
        <p className="note" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
