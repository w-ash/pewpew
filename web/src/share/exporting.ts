// An export asked of the server, and the two ways the page hands one on: a file the browser
// downloads, and a form that posts a share to the Gallery.
import type { ExportedMessage } from "../wire/protocol";
import type { Wire } from "../wire/store";

/** Ask for an export of the saved looks `looks` (null: every one), as a share envelope when `share`.
 * Returns the answer, or why there is none: the server's refusal, or a connection that is down. */
export async function askExport(wire: Wire, looks: readonly string[] | null, share: boolean): Promise<ExportedMessage | string> {
  const before = wire.store.getState().refusals.export;
  const took = await wire.sender.ask({ type: "export", looks, share });
  const answer = wire.store.exported;
  if (took && answer) return answer;
  const refusal = wire.store.getState().refusals.export;
  return refusal && refusal !== before ? refusal.reason : "The export did not go out: the connection is down.";
}

/** Save `data` as JSON in a file named `name`, as a download. */
export function download(name: string, data: unknown): void {
  const url = URL.createObjectURL(new Blob([`${JSON.stringify(data, null, 2)}\n`], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  // The download has its copy once the click is handled.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Post `envelope` to the Gallery at `gallery` (no trailing slash) from a form that opens a new tab. A
 * form's post is a top-level navigation: it needs no CORS, and `rel="noreferrer"` keeps the Console's
 * address out of the request. Call it in the press that asks for it, since a popup blocker lets a new
 * tab open only then. */
export function postShare(gallery: string, envelope: unknown): void {
  const form = document.createElement("form");
  form.method = "post";
  form.action = `${gallery}/api/shares`;
  form.target = "_blank";
  form.rel = "noreferrer";
  const field = document.createElement("input");
  field.type = "hidden";
  field.name = "envelope";
  field.value = JSON.stringify(envelope);
  form.append(field);
  document.body.append(form);
  form.submit();
  form.remove();
}
