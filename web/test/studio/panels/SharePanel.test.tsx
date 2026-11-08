import { afterEach, expect, test, vi } from "vitest";
import { render } from "vitest-browser-react";
import { SharePanel } from "../../../src/studio/panels/SharePanel";
import { DEFAULT_ARRANGEMENT, useShare } from "../../../src/studio/store/share";

afterEach(() => vi.restoreAllMocks());

test("with no clipboard the link is selected, not claimed copied", async () => {
  useShare.getState().load(DEFAULT_ARRANGEMENT, { mode: "shared", id: "X" });
  vi.spyOn(navigator, "clipboard", "get").mockReturnValue(undefined as unknown as Clipboard);
  const screen = await render(<SharePanel />);
  await screen.getByRole("button", { name: "Copy link" }).click();
  await expect.element(screen.getByRole("button", { name: /^Selected/ })).toBeInTheDocument();
  await expect.element(screen.getByTestId("share-link")).toHaveFocus();
});
