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
import { useMedia, WIDE } from "../design/useMedia";
import { canArrange, useRefusal, useWire } from "../wire/store";
import { ArrangementPanel } from "./ArrangementPanel";
import { useDocEditor } from "./doc";
import { GizmoToolbar, useGizmoTools } from "./gizmoTools";
import { useEditorKeys } from "./keys";
import { IssueList, ReportPanel } from "./ReportPanel";
import { retryArrange, useArrangeSync, useArrangeSyncState, useEngineArrangement, useRigIsCurrent } from "./sync";

// Where the last press or focus must be for Delete and Backspace to delete what is selected: the layout
// panel and the 3D view.
const EDITOR_SCOPE = ".arrange-panel, .stage-3d";

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

/** The layout panel: the build-day tools (input-end markers, blink), what became of the last edit (the
 * engine's refusal with its issues, or edits a layout from elsewhere replaced), and the arrangement
 * editor. Each edit runs live once edits settle (sync.ts); undo and redo are this page's. Open only on a
 * run that takes `arrange`; read-only while the connection is down. On a phone, the 3D view's gizmo
 * tools sit here, off its small canvas. */
export function ArrangeSlot({ onClose, onReport }: { onClose(): void; onReport(): void }) {
  const { refused, notice } = useArrangeSync();
  useEditorKeys(false, EDITOR_SCOPE);
  const { engine, rig, editor, current } = useEditor();
  const catalog = use(partsOrNull(`${rig?.catalog_digest ?? ""}#0`));
  const refusal = useRefusal("arrange");
  const problems = useWire((s) => s.report?.issues.filter((i) => i.level !== "warning").length ?? 0);
  const connected = useWire((s) => s.connected);
  const wide = useMedia(WIDE);
  const gizmo = useGizmoTools((s) => s.shown) && !wide;
  return (
    <Panel title="layout" onClose={onClose}>
      <div className="arrange-panel">
        <LayoutTools />
        {!connected ? (
          <Banner tone="warning">
            Reconnecting to the engine: the layout is read-only until it is back. An edit not yet taken goes
            then, unless the layout changed meanwhile.
          </Banner>
        ) : notice ? (
          <Banner tone="warning" onDismiss={() => useArrangeSyncState.setState({ notice: null })}>
            {notice}
          </Banner>
        ) : (
          refused &&
          refusal && (
            <Banner>
              <div className="fields">
                <span>The engine did not take this edit: {refusal.reason}</span>
                {refusal.issues.length > 0 && <IssueList issues={refusal.issues} />}
                {!current && (
                  <div className="row wrap">
                    <Button onPress={retryArrange}>send again</Button>
                  </div>
                )}
              </div>
            </Banner>
          )
        )}
        {gizmo && (
          <div className="row wrap" role="group" aria-label="Gizmo tools">
            <GizmoToolbar />
          </div>
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
