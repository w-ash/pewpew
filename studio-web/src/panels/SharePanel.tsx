import { useRef, useState } from "react";
import { ApiError } from "@/api/client";
import { saveArrangement } from "@/api/endpoints";
import type { Issue } from "@/api/types";
import { useDoc } from "@/store/doc";
import { IssueList } from "./ReportPanel";
import { Button, SectionHeading } from "./ui";

export function shareUrl(id: string, origin = window.location.origin) {
  return `${origin}/a/${id}`;
}

export function SharePanel() {
  const arrangement = useDoc((s) => s.history.present);
  const share = useDoc((s) => s.share);
  const markSaved = useDoc((s) => s.markSaved);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<{
    message: string;
    issues: Issue[];
  } | null>(null);
  const [copied, setCopied] = useState<"copied" | "selected" | null>(null);
  const linkInput = useRef<HTMLInputElement>(null);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const { id } = await saveArrangement(arrangement);
      markSaved(arrangement, id);
      if (useDoc.getState().share.mode === "shared")
        window.history.replaceState(null, "", `/a/${id}`);
    } catch (e) {
      if (e instanceof ApiError) {
        setError({
          message:
            e.status === 429
              ? "Too many saves from this address. Wait a minute and try again."
              : e.message,
          issues: e.issues,
        });
      } else {
        setError({ message: "The server could not be reached.", issues: [] });
      }
    } finally {
      setSaving(false);
    }
  };

  const link = share.mode === "shared" ? shareUrl(share.id) : null;

  // The clipboard API is missing outside a secure context and can be denied;
  // then the link is selected for a manual copy.
  const copy = async (text: string) => {
    try {
      if (!navigator.clipboard) throw new Error("no clipboard");
      await navigator.clipboard.writeText(text);
      setCopied("copied");
    } catch {
      linkInput.current?.focus();
      linkInput.current?.select();
      setCopied("selected");
    }
    setTimeout(() => setCopied(null), 2500);
  };

  return (
    <div className="flex flex-col gap-5">
      <section>
        <SectionHeading>Share link</SectionHeading>
        {share.mode === "shared" && (
          <p className="mb-3 text-sm text-muted">
            This is a shared arrangement. Links never change: any edit makes
            your own copy, and saving it gives a new link.
          </p>
        )}
        {share.mode === "fork" && (
          <p className="mb-3 text-sm text-muted">
            Your copy of <span className="font-data">/a/{share.from}</span>.
            Save it to get a link of its own.
          </p>
        )}
        {link ? (
          <div className="flex flex-col gap-2">
            <input
              ref={linkInput}
              readOnly
              value={link}
              aria-label="Share link"
              data-testid="share-link"
              onFocus={(e) => e.target.select()}
              className="h-11 w-full rounded-md border border-line bg-bg px-2 font-data text-sm text-ink"
            />
            <div className="flex gap-2">
              <Button variant="primary" onClick={() => copy(link)}>
                {copied === "copied"
                  ? "Copied"
                  : copied === "selected"
                    ? "Selected: copy it from the field"
                    : "Copy link"}
              </Button>
            </div>
          </div>
        ) : (
          <Button
            variant="primary"
            onClick={save}
            disabled={saving || share.mode === "loading"}
          >
            {saving ? "Saving…" : "Save and get a link"}
          </Button>
        )}
        {error && (
          <div className="mt-3 flex flex-col gap-2" role="alert">
            <p className="text-sm text-error">{error.message}</p>
            {error.issues.length > 0 && <IssueList issues={error.issues} />}
          </div>
        )}
      </section>
      <section>
        <SectionHeading>What a link holds</SectionHeading>
        <p className="text-sm text-muted">
          The arrangement only: fixtures, groups, wiring and the parts on their
          ends. The effect and its controls are not saved.
        </p>
      </section>
    </div>
  );
}
