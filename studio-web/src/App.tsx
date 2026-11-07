import { useEffect, useMemo, useState } from "react";
import { ApiError } from "./api/client";
import { getArrangement } from "./api/endpoints";
import { useCatalog, useCompiled } from "./api/queries";
import type { Issue } from "./api/types";
import { asArrangement, remove } from "./editor/arrangement";
import { cn } from "./lib/cn";
import { ArrangementPanel } from "./panels/ArrangementPanel";
import { EffectPanel } from "./panels/EffectPanel";
import { ReportPanel } from "./panels/ReportPanel";
import { SharePanel } from "./panels/SharePanel";
import { SessionClient } from "./session/client";
import { useDoc } from "./store/doc";
import { useSession } from "./store/session";
import { Stage } from "./viewer/Stage";

type Tab = "arrange" | "effect" | "report" | "share";
const TABS: Array<{ id: Tab; label: string }> = [
  { id: "arrange", label: "Arrange" },
  { id: "effect", label: "Effect" },
  { id: "report", label: "Report" },
  { id: "share", label: "Share" },
];

const SHARE_PATH = /^\/a\/([A-Za-z0-9_-]{22})\/?$/;

export function shareIdFromPath(pathname: string): string | null {
  return SHARE_PATH.exec(pathname)?.[1] ?? null;
}

function useSharedLink(setNotice: (notice: string | null) => void) {
  // biome-ignore lint/correctness/useExhaustiveDependencies: runs once, for the URL the page opened on.
  useEffect(() => {
    const id = shareIdFromPath(window.location.pathname);
    if (!id) return;
    const { load, setShare } = useDoc.getState();
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
  }, []);

  const share = useDoc((s) => s.share);
  useEffect(() => {
    if (share.mode === "fork" && window.location.pathname.startsWith("/a/")) {
      window.history.replaceState(null, "", "/");
    }
  }, [share]);
}

function useShortcuts() {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (
        el &&
        (el.isContentEditable ||
          ["INPUT", "SELECT", "TEXTAREA"].includes(el.tagName))
      )
        return;
      const doc = useDoc.getState();
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) doc.redo();
        else doc.undo();
      } else if (mod && e.key.toLowerCase() === "y") {
        e.preventDefault();
        doc.redo();
      } else if (
        (e.key === "Delete" || e.key === "Backspace") &&
        doc.selection
      ) {
        e.preventDefault();
        doc.commit(remove(doc.history.present, doc.selection));
        doc.select(null);
      } else if (e.key === "Escape") {
        doc.select(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}

export function App({ client }: { client?: SessionClient }) {
  const [session] = useState(() => client ?? new SessionClient());
  const [tab, setTab] = useState<Tab>("arrange");
  const [notice, setNotice] = useState<string | null>(null);
  const arrangement = useDoc((s) => s.history.present);
  const share = useDoc((s) => s.share);
  const catalog = useCatalog();
  const {
    query: compiled,
    rig,
    current,
  } = useCompiled(arrangement, share.mode !== "loading");
  const refusal = useSession((s) => s.refusal);
  const [showRefusal, setShowRefusal] = useState(false);

  useSharedLink(setNotice);
  useShortcuts();

  useEffect(() => {
    session.start();
    return () => session.stop();
  }, [session]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: bind follows each accepted compile, not each edit.
  useEffect(() => {
    if (current) session.bind(arrangement);
  }, [rig, current]);

  useEffect(() => {
    if (!refusal) return;
    setShowRefusal(true);
    const timer = setTimeout(() => setShowRefusal(false), 4000);
    return () => clearTimeout(timer);
  }, [refusal]);

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
    <div className="grid min-h-dvh grid-cols-1 gap-4 p-4 lg:h-dvh lg:grid-cols-[minmax(0,1fr)_360px] lg:gap-5">
      <main className="h-[56vh] min-h-[320px] lg:h-auto lg:min-h-0">
        <Stage rig={rig} catalog={catalog.data ?? null} />
      </main>
      <aside className="flex min-h-0 flex-col gap-4 lg:overflow-hidden">
        <header className="shrink-0">
          <h1 className="font-display text-2xl leading-tight font-semibold">
            pewpew studio
          </h1>
          <p className="mt-1 text-sm text-muted">
            Arrange LED fixtures in 3D and run pewpew's effects on them.
          </p>
        </header>

        {share.mode === "loading" && (
          <Banner>Loading the shared arrangement…</Banner>
        )}
        {share.mode === "shared" && (
          <Banner>
            Shared arrangement{" "}
            <span className="font-data">{share.id.slice(0, 8)}…</span>,
            read-only. Your first edit makes your own copy.
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
        {showRefusal && refusal && (
          <Banner tone="warning">{refusal.reason}</Banner>
        )}

        <div
          role="tablist"
          aria-label="Panels"
          className="grid shrink-0 grid-cols-4 overflow-hidden rounded-md border border-line"
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
              className={cn(
                "min-h-11 text-xs font-medium uppercase tracking-wider not-first:border-l not-first:border-line",
                tab === t.id
                  ? "bg-ink text-surface"
                  : "text-muted hover:text-ink",
              )}
            >
              {t.label}
              {t.id === "report" && counts.error + counts.violation > 0 && (
                <span className="ml-1 rounded bg-error px-1 text-[10px] text-white">
                  {counts.error + counts.violation}
                </span>
              )}
            </button>
          ))}
        </div>

        <div
          role="tabpanel"
          id={`panel-${tab}`}
          aria-labelledby={`tab-${tab}`}
          className="min-h-0 flex-1 pb-6 lg:overflow-y-auto lg:pr-1"
        >
          {tab === "arrange" && (
            <fieldset
              disabled={share.mode === "loading"}
              className="min-w-0 disabled:opacity-50"
            >
              <ArrangementPanel
                catalog={catalog.data ?? null}
                rig={rig}
                rigIsCurrent={current}
              />
            </fieldset>
          )}
          {tab === "effect" && <EffectPanel client={session} />}
          {tab === "report" && (
            <ReportPanel
              report={rig?.report ?? null}
              issues={issues}
              stale={!current}
            />
          )}
          {tab === "share" && <SharePanel />}
        </div>
      </aside>
    </div>
  );
}

function Banner({
  children,
  tone = "info",
  onDismiss,
}: {
  children: React.ReactNode;
  tone?: "info" | "warning" | "error";
  onDismiss?: () => void;
}) {
  return (
    <div
      role={tone === "info" ? "status" : "alert"}
      className={cn(
        "flex shrink-0 items-start justify-between gap-2 rounded-md border px-3 py-2 text-sm",
        tone === "info" && "border-line bg-surface",
        tone === "warning" && "border-warning bg-warning/10",
        tone === "error" && "border-error bg-error/10",
      )}
    >
      <span>{children}</span>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          className="-my-2 min-h-11 min-w-11 text-muted"
        >
          ✕
        </button>
      )}
    </div>
  );
}
