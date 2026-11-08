import { ArmStatus } from "../design/press";
import { Badge } from "../design/Badge";
import { Banner } from "../design/Banner";
import { StepStatus } from "../design/StepStatus";
import { useMedia, WIDE } from "../design/useMedia";
import { useWire, WireContext } from "../wire/store";
import { useEffect, useMemo, useState } from "react";
import { ApiError } from "./api/fetch";
import { compileArrangement, getArrangement } from "./api/endpoints";
import { useCatalog, useCompiled } from "./api/queries";
import type { Arrangement, Issue } from "./api/types";
import { asArrangement } from "../arrange/arrangement";
import { useEditorKeys } from "../arrange/keys";
import { ArrangementPanel } from "../arrange/ArrangementPanel";
import { useDocEditor } from "../arrange/doc";
import { ReportPanel } from "../arrange/ReportPanel";
import { EffectPanel } from "./panels/EffectPanel";
import { SharePanel } from "./panels/SharePanel";
import { SessionClient } from "./session/client";
import { useShare } from "./store/share";
import { useSettledPreview } from "../rig3d/dragPreview";
import { Stage } from "../rig3d/Stage";

type Tab = "arrange" | "effect" | "report" | "share";
const TABS: Array<{ id: Tab; label: string }> = [
  { id: "arrange", label: "Arrange" },
  { id: "effect", label: "Effect" },
  { id: "report", label: "Report" },
  { id: "share", label: "Share" },
];

const SHARE_PATH = /^\/a\/([A-Za-z0-9_-]{22})\/?$/;

function shareIdFromPath(pathname: string): string | null {
  return SHARE_PATH.exec(pathname)?.[1] ?? null;
}

function useSharedLink(setNotice: (notice: string | null) => void) {
  // Runs once, for the URL the page opened on.
  useEffect(() => {
    const id = shareIdFromPath(window.location.pathname);
    if (!id) return;
    const { load, setShare } = useShare.getState();
    setShare({ mode: "loading", id });
    getArrangement(id)
      .then((body) => {
        const arrangement = asArrangement(body);
        if (!arrangement) throw new Error("not an arrangement");
        load(arrangement, { mode: "shared", id });
      })
      .catch((e) => {
        setShare({ mode: "draft" });
        window.history.replaceState(null, "", "/");
        setNotice(
          e instanceof ApiError && e.status === 404
            ? `No shared arrangement has the id ${id}. Showing the default instead.`
            : "The shared arrangement could not be loaded. Showing the default instead.",
        );
      });
  // oxlint-disable-next-line react-hooks/exhaustive-deps -- runs once, for the URL the page opened on
  }, []);

  const share = useShare((s) => s.share);
  useEffect(() => {
    if (share.mode === "fork" && window.location.pathname.startsWith("/a/")) {
      window.history.replaceState(null, "", "/");
    }
  }, [share]);
}

/** The server checks every field the editors read, so only a file it compiles reaches the document. */
async function checkImport(next: Arrangement): Promise<string | null> {
  try {
    await compileArrangement(next);
    return null;
  } catch (e) {
    return e instanceof ApiError && e.status === 422
      ? e.issues.map((i) => i.message).join("; ") || e.message
      : "the server could not check it";
  }
}

export function App({ client }: { client?: SessionClient }) {
  const [session] = useState(() => client ?? new SessionClient());
  const [wire] = useState(() => ({
    store: session.wire,
    sender: session.socket,
  }));
  return (
    <WireContext.Provider value={wire}>
      <Studio session={session} />
    </WireContext.Provider>
  );
}

function Studio({ session }: { session: SessionClient }) {
  const wide = useMedia(WIDE);
  const power = useWire((s) => s.power);
  const [tab, setTab] = useState<Tab>("arrange");
  const [notice, setNotice] = useState<string | null>(null);
  const editor = useDocEditor();
  const { arrangement } = editor;
  const share = useShare((s) => s.share);
  const catalog = useCatalog();
  const {
    query: compiled,
    rig,
    current,
    answered,
  } = useCompiled(arrangement, share.mode !== "loading");

  useSettledPreview(answered);
  useSharedLink(setNotice);
  useEditorKeys(true);

  useEffect(() => {
    session.start();
    return () => session.stop();
  }, [session]);

  // Bind follows each accepted compile, not each edit.
  useEffect(() => {
    if (current) session.bind(arrangement);
  // oxlint-disable-next-line react-hooks/exhaustive-deps -- bind follows each accepted compile, not each edit
  }, [rig, current]);

  const compileError =
    compiled.error instanceof ApiError ? compiled.error : null;
  const issues: Issue[] = useMemo(() => {
    if (compiled.isError) {
      return compileError?.issues.length
        ? compileError.issues
        : [
            {
              level: "error",
              code: "compile",
              message: compiled.error?.message ?? "compile failed",
              ref: null,
            },
          ];
    }
    return rig?.issues ?? [];
  }, [compiled.isError, compiled.error, compileError, rig]);
  const counts = {
    error: issues.filter((i) => i.level === "error").length,
    violation: issues.filter((i) => i.level === "violation").length,
  };

  return (
    <div className="studio" data-wide={wide || undefined}>
      <main className="studio-stage-area">
        <Stage rig={rig} catalog={catalog.data ?? null} />
      </main>
      <aside className="studio-side">
        <header className="studio-head">
          <h1 className="t-display">pewpew studio</h1>
          <p className="note">
            Arrange LED fixtures in 3D and run pewpew's effects on them.
          </p>
        </header>

        {share.mode === "loading" && (
          <Banner tone="info">Loading the shared arrangement…</Banner>
        )}
        {share.mode === "shared" && (
          <Banner tone="info">
            Shared arrangement{" "}
            <span className="t-code">{share.id.slice(0, 8)}…</span>, read-only.
            Your first edit makes your own copy.
          </Banner>
        )}
        {notice && (
          <Banner tone="warning" onDismiss={() => setNotice(null)}>
            {notice}
          </Banner>
        )}
        {catalog.isError && (
          <Banner tone="error">The fixture catalog could not be loaded.</Banner>
        )}
        {compiled.isError && (
          <Banner tone="error">
            {compileError?.status === 422
              ? `This arrangement does not compile: ${issues[0]?.message}.`
              : `The server could not compile this arrangement (${compiled.error?.message}).`}
            {rig && " The view shows the last one that did."}
          </Banner>
        )}

        <div
          role="tablist"
          aria-label="Panels"
          className="studio-tabs"
        >
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              id={`tab-${t.id}`}
              aria-selected={tab === t.id}
              aria-controls={`panel-${t.id}`}
              onClick={() => setTab(t.id)}
              className="button"
              data-variant="tertiary"
            >
              {t.label}
              {t.id === "report" && counts.error + counts.violation > 0 && (
                <Badge tone="danger">{counts.error + counts.violation}</Badge>
              )}
            </button>
          ))}
        </div>

        <div
          role="tabpanel"
          id={`panel-${tab}`}
          aria-labelledby={`tab-${tab}`}
          className="studio-tabpanel"
        >
          {tab === "arrange" && (
            <fieldset disabled={share.mode === "loading"}>
              <ArrangementPanel
                {...editor}
                catalog={catalog.data ?? null}
                rig={rig}
                rigIsCurrent={current}
                checkImport={checkImport}
              />
            </fieldset>
          )}
          {tab === "effect" && <EffectPanel />}
          {tab === "report" && (
            <ReportPanel
              report={rig?.report ?? null}
              issues={issues}
              stale={!current}
              power={power}
              arrangement={arrangement}
              onCommit={editor.onCommit}
              capDisabled={share.mode === "loading"}
            />
          )}
          {tab === "share" && <SharePanel />}
        </div>
      </aside>
      <ArmStatus />
      <StepStatus />
    </div>
  );
}
