import { Block } from "../../design/Block";
import { Button } from "../../design/Button";
import { useRef, useState } from "react";
import { ApiError } from "../api/fetch";
import { saveArrangement } from "../api/endpoints";
import type { Issue } from "../api/types";
import { useDoc } from "../store/doc";
import { IssueList } from "./ReportPanel";

/** Whether `text` reached the clipboard: the API is missing outside a secure context and can be denied. */
async function writeClipboard(text: string): Promise<boolean> {
  if (!navigator.clipboard) return false;
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

function shareUrl(id: string, origin = window.location.origin) {
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
    }
    setSaving(false);
  };

  const link = share.mode === "shared" ? shareUrl(share.id) : null;

  // A link the clipboard did not take is selected for a manual copy.
  const copy = async (text: string) => {
    const copied = await writeClipboard(text);
    if (!copied) {
      linkInput.current?.focus();
      linkInput.current?.select();
    }
    setCopied(copied ? "copied" : "selected");
    setTimeout(() => setCopied(null), 2500);
  };

  return (
    <div className="studio-panel">
      <Block className="fields" title="Share link">
        {share.mode === "shared" && (
          <p className="t-label">
            This is a shared arrangement. Links never change: any edit makes
            your own copy, and saving it gives a new link.
          </p>
        )}
        {share.mode === "fork" && (
          <p className="t-label">
            Your copy of <span className="t-code">/a/{share.from}</span>. Save
            it to get a link of its own.
          </p>
        )}
        {link ? (
          <div className="fields">
            <input
              ref={linkInput}
              readOnly
              value={link}
              aria-label="Share link"
              data-testid="share-link"
              onFocus={(e) => e.target.select()}
              className="t-code"
            />
            <div className="row wrap">
              <Button variant="primary" onPress={() => void copy(link)}>
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
            onPress={() => void save()}
            disabled={saving || share.mode === "loading"}
          >
            {saving ? "Saving…" : "Save and get a link"}
          </Button>
        )}
        {error && (
          <div className="fields" role="alert">
            <p className="refusal">{error.message}</p>
            {error.issues.length > 0 && <IssueList issues={error.issues} />}
          </div>
        )}
      </Block>
      <Block className="fields" title="What a link holds">
        <p className="t-label">
          The arrangement only: fixtures, groups, wiring and the parts on their
          ends. The effect and its controls are not saved.
        </p>
      </Block>
    </div>
  );
}
