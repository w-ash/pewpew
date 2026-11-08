// Publish in the Console's layout panel (capability "publish"), and the looks' export behind the deck's
// "⋯" (capability "export").
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "../../src/app/App";
import { EMPTY_ARRANGEMENT, useDoc } from "../../src/arrange/doc";
import { createHistory } from "../../src/arrange/history";
import { PARTS_URL } from "../../src/rig/loadParts";
import { PUBLIC_NOTE, YOUR_CALL } from "../../src/share/Publish";
import type { ServerMessage } from "../../src/wire/protocol";
import { first, GREETING, hello, LATER } from "../fixtures/messages";
import { renderWired } from "../harness";
import { partsCatalog } from "../rig3d/rig";

const realFetch = globalThis.fetch;

/** What each form the page submitted holds. */
interface Posted {
  readonly method: string;
  readonly action: string;
  readonly target: string;
  readonly rel: string;
  readonly fields: readonly { readonly type: string; readonly name: string; readonly value: string }[];
}
let posted: Posted[] = [];

beforeEach(() => {
  posted = [];
  useDoc.setState({ history: createHistory(EMPTY_ARRANGEMENT), selection: null, loads: 0, readOnly: false });
  vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) =>
    input === PARTS_URL ? Response.json(partsCatalog) : realFetch(input, init),
  );
  vi.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(function (this: HTMLFormElement) {
    const fields = [...this.querySelectorAll("input")].map((i) => ({ type: i.type, name: i.name, value: i.value }));
    posted.push({ method: this.method, action: this.action, target: this.target, rel: this.rel, fields });
  });
  vi.spyOn(HTMLFormElement.prototype, "requestSubmit").mockImplementation(() => {
    throw new Error("the page submits with submit()");
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

/** An engine run with `capabilities` on the golden's rig. */
const run = (capabilities: readonly string[]): readonly ServerMessage[] => [
  ...GREETING.map((m) => (m.type === "hello" ? hello({ capabilities }) : m)),
  first("layout", LATER),
];
const PUBLISHES = run(["ack", "look", "arrange", "export", "publish"]);
const GALLERY = "https://gallery.example";
const ENVELOPE = { format: "pewpew.share", version: 1, arrangement: { fixtures: [] }, looks: { version: 4, current: "warm", looks: { warm: {} }, cycle: [] } };
/** A share of a layout with a name and public notes. */
const NOTED = { ...ENVELOPE, arrangement: { name: "porch rig", public_notes: "Two rings.\n<b>not markup</b>", fixtures: [] } };

async function openPublish(heard = PUBLISHES) {
  const wired = await renderWired(<App />, heard);
  await wired.screen.getByRole("button", { name: "layout" }).click();
  await wired.screen.getByRole("button", { name: "publish" }).click();
  return wired;
}

test("Publish picks the current look and the favorites, asks for the share, and posts only after the confirmation's press", async () => {
  const { screen, sent, receive, answer } = await openPublish();
  const panel = screen.getByRole("region", { name: "publish" });
  await expect.element(panel.getByRole("switch", { name: "warm" })).toBeChecked();
  await expect.element(panel.getByRole("switch", { name: "cool" })).toBeChecked();
  await panel.getByRole("switch", { name: "cool" }).click();
  await panel.getByRole("button", { name: "next" }).click();
  expect(sent.at(-1)).toEqual({ type: "export", looks: ["warm"], share: true });
  expect(posted).toEqual([]);
  receive({ type: "exported", id: 1, file: ENVELOPE, gallery: GALLERY });
  await answer();
  await expect.element(panel.getByText(PUBLIC_NOTE)).toBeVisible();
  expect(PUBLIC_NOTE).toBe("This is public: anyone with the link sees this layout and these looks. Board addresses are removed.");
  await expect.element(panel.getByText(/gallery\.example/)).toBeVisible();
  expect(posted).toEqual([]);
  await panel.getByRole("button", { name: "publish" }).click();
  expect(posted).toEqual([
    {
      method: "post",
      action: `${GALLERY}/api/shares`,
      target: "_blank",
      rel: "noreferrer",
      fields: [{ type: "hidden", name: "envelope", value: JSON.stringify(ENVELOPE) }],
    },
  ]);
  // The form is gone once submitted.
  expect(document.querySelector("form")).toBeNull();
});

test("the confirmation shows, as plain text, everything the share makes public, and the public notes can stay out", async () => {
  const { screen, receive, answer } = await openPublish();
  const panel = screen.getByRole("region", { name: "publish" });
  await panel.getByRole("button", { name: "next" }).click();
  receive({ type: "exported", id: 1, file: NOTED, gallery: GALLERY });
  await answer();
  await expect.element(panel.getByText(YOUR_CALL)).toBeVisible();
  const shown = (panel.element() as HTMLElement).innerText;
  for (const part of ["porch rig", "Two rings.", "<b>not markup</b>", "warm", PUBLIC_NOTE]) expect(shown).toContain(part);
  expect(panel.element().querySelector("b")).toBeNull();
  const notes = panel.getByRole("switch", { name: "share the public notes" });
  await expect.element(notes).toBeChecked();
  await notes.click();
  await expect.element(panel.getByText("(left out of this share)")).toBeVisible();
  await panel.getByRole("button", { name: "publish" }).click();
  const { public_notes: _, ...without } = NOTED.arrangement;
  expect(JSON.parse(posted[0]!.fields[0]!.value)).toEqual({ ...NOTED, arrangement: without });
  await notes.click();
  await panel.getByRole("button", { name: "publish" }).click();
  expect(JSON.parse(posted[1]!.fields[0]!.value)).toEqual(NOTED);
});

test("a share with no name and no public notes says so and has no switch", async () => {
  const { screen, receive, answer } = await openPublish();
  const panel = screen.getByRole("region", { name: "publish" });
  await panel.getByRole("button", { name: "next" }).click();
  receive({ type: "exported", id: 1, file: ENVELOPE, gallery: GALLERY });
  await answer();
  await expect.element(panel.getByText("(none)")).toBeVisible();
  await expect.element(panel.getByRole("switch")).not.toBeInTheDocument();
});

test("a refused export shows its reason in place and posts nothing", async () => {
  const { screen, receive, answer } = await openPublish();
  const panel = screen.getByRole("region", { name: "publish" });
  await panel.getByRole("button", { name: "next" }).click();
  receive({ type: "refused", control: "export", name: null, id: 1, reason: "look warm does not check: no layers" });
  await answer(false);
  await expect.element(panel.getByRole("alert")).toHaveTextContent("look warm does not check: no layers");
  await expect.element(panel.getByText(PUBLIC_NOTE)).not.toBeInTheDocument();
  expect(posted).toEqual([]);
});

test("with no look picked, next is off", async () => {
  const { screen, sent } = await openPublish();
  const panel = screen.getByRole("region", { name: "publish" });
  await panel.getByRole("switch", { name: "warm" }).click();
  await panel.getByRole("switch", { name: "cool" }).click();
  await expect.element(panel.getByRole("button", { name: "next" })).toBeDisabled();
  expect(sent.filter((m) => m.type === "export")).toEqual([]);
});

test("without the capability, the layout panel has no Publish", async () => {
  const { screen } = await renderWired(<App />, run(["ack", "look", "arrange", "export"]));
  await screen.getByRole("button", { name: "layout" }).click();
  await expect.element(screen.getByRole("button", { name: "report" })).toBeVisible();
  await expect.element(screen.getByRole("button", { name: "publish" })).not.toBeInTheDocument();
});

/** Open the deck's "⋯". */
async function openMore(heard: readonly ServerMessage[]) {
  const wired = await renderWired(<App />, heard);
  await wired.screen.getByRole("button", { name: /^more:/ }).click();
  return wired;
}

test("export looks asks for every saved look and downloads the file as looks.json", async () => {
  const clicked: { download: string; href: string }[] = [];
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
    clicked.push({ download: this.download, href: this.href });
  });
  const blobs: Blob[] = [];
  const made = vi.spyOn(URL, "createObjectURL").mockImplementation((blob) => {
    blobs.push(blob as Blob);
    return "blob:looks";
  });
  const { screen, sent, receive, answer } = await openMore(run(["ack", "look", "export"]));
  await screen.getByRole("button", { name: "export looks" }).click();
  expect(sent.at(-1)).toEqual({ type: "export", looks: null, share: false });
  const file = { version: 4, current: "warm", looks: { warm: { layers: [] } }, cycle: ["warm"] };
  receive({ type: "exported", id: 1, file, gallery: null });
  await answer();
  await expect.poll(() => clicked).toEqual([{ download: "looks.json", href: "blob:looks" }]);
  expect(made).toHaveBeenCalledOnce();
  expect(JSON.parse(await blobs[0]!.text())).toEqual(file);
  expect(blobs[0]!.type).toBe("application/json");
});

test("a refused export shows its reason under the button", async () => {
  const { screen, receive, answer } = await openMore(run(["ack", "look", "export"]));
  await screen.getByRole("button", { name: "export looks" }).click();
  receive({ type: "refused", control: "export", name: null, id: 1, reason: "no saved looks" });
  await answer(false);
  await expect.element(screen.getByRole("alert").filter({ hasText: "no saved looks" })).toBeVisible();
});

test("without the capability, the deck's ⋯ has no export", async () => {
  const { screen } = await openMore(run(["ack", "look"]));
  await expect.element(screen.getByRole("combobox").or(screen.getByText("fade:")).first()).toBeInTheDocument();
  await expect.element(screen.getByRole("button", { name: "export looks" })).not.toBeInTheDocument();
});
