// The layout editor and the report in the Console's slot, loaded on demand (app/App.tsx) with the rest of
// src/arrange: the page always loads none of it.
import { use } from "react";
import { Badge } from "../design/Badge";
import { Banner } from "../design/Banner";
import { Button } from "../design/Button";
import { Panel } from "../design/Panel";
import { LayoutTools } from "../layout/LayoutTools";
import { loadParts } from "../rig/loadParts";
import type { PartsCatalog } from "../rig/parts";
import { canArrange, useRefusal, useWire } from "../wire/store";
import { ArrangementPanel } from "./ArrangementPanel";
import { useDocEditor } from "./doc";
import { useEditorKeys } from "./keys";
import { IssueList, ReportPanel } from "./ReportPanel";
import { useArrangeSync, useEngineArrangement, useRigIsCurrent } from "./sync";

// The parts catalog, or null when it does not load: the editor then offers the default fixture type and
// no attachments, and the 3D view says why it draws no models.
let parts: { readonly key: string; readonly promise: Promise<PartsCatalog | null> } | null = null;

function partsOrNull(key: string): Promise<PartsCatalog | null> {
  if (parts?.key !== key) parts = { key, promise: loadParts(key).catch(() => null) };
  return parts.promise;
}

/** The engine's arrangement as the editor holds it: what it edits, whether the engine's rig is its
 * compile, and the editor's history. */
function useEditor() {
  const engine = useEngineArrangement();
  const rig = useWire((s) => s.map?.rig ?? null);
  const editor = useDocEditor();
  const current = useRigIsCurrent();
  return { engine, rig, editor, current };
}

/** The layout panel: the build-day tools (input-end markers, blink), the engine's refusal of the last
 * edit with its issues, and the arrangement editor. Each edit runs live once edits settle (sync.ts); undo
 * and redo are this page's. Open only on a run that takes `arrange`. */
export function ArrangeSlot({ onClose, onReport }: { onClose(): void; onReport(): void }) {
  const { refused } = useArrangeSync();
  useEditorKeys(false);
  const { engine, rig, editor, current } = useEditor();
  const catalog = use(partsOrNull(`${rig?.catalog_digest ?? ""}#0`));
  const refusal = useRefusal("arrange");
  const problems = useWire((s) => s.report?.issues.filter((i) => i.level !== "warning").length ?? 0);
  return (
    <Panel title="layout" onClose={onClose}>
      <div className="arrange-panel">
        <LayoutTools />
        {refused && refusal && (
          <Banner>
            <div className="fields">
              <span>The engine did not take this edit: {refusal.reason}</span>
              {refusal.issues.length > 0 && <IssueList issues={refusal.issues} />}
            </div>
          </Banner>
        )}
        <div className="row wrap">
          <Button onPress={onReport} title="power, wiring and controllers of the running rig">
            report
            {problems > 0 && <Badge tone="danger">{problems}</Badge>}
          </Button>
        </div>
        {engine ? (
          <ArrangementPanel
            {...editor}
            catalog={catalog}
            rig={rig}
            rigIsCurrent={current}
          />
        ) : (
          <p className="note">waiting for the arrangement from the engine</p>
        )}
      </div>
    </Panel>
  );
}

/** The power, wiring and controller report of the running rig, and its live draw. On a run that takes
 * `arrange`, it edits the power cap too, as the layout panel's edits run. */
export function ReportSlot({ onClose }: { onClose(): void }) {
  const editable = useWire(canArrange);
  return (
    <Panel title="report" onClose={onClose}>
      <div className="arrange-panel">{editable ? <EditableReport /> : <Report />}</div>
    </Panel>
  );
}

function Report() {
  const report = useWire((s) => s.report);
  const power = useWire((s) => s.power);
  return <ReportPanel report={report?.report ?? null} issues={report?.issues ?? []} stale={false} power={power} />;
}

function EditableReport() {
  useArrangeSync();
  const { engine, editor, current } = useEditor();
  const report = useWire((s) => s.report);
  const power = useWire((s) => s.power);
  return (
    <ReportPanel
      report={report?.report ?? null}
      issues={report?.issues ?? []}
      stale={!current}
      power={power}
      arrangement={engine ? editor.arrangement : undefined}
      onCommit={editor.onCommit}
    />
  );
}
