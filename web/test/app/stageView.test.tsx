import { expect, test } from "vitest";
import { App } from "../../src/app/App";
import { first, LATER } from "../fixtures/messages";
import { renderWired } from "../harness";

const RIG_LAYOUT = first("layout", LATER);

test("the stage's 2D/3D switch shows only while the map is a rig", async () => {
  const { screen, receive } = await renderWired(<App />);
  // The greeting's map is a line: no rig, so no 3D view and no switch.
  await expect.element(screen.getByRole("img", { name: "preview of the LEDs" })).toBeInTheDocument();
  expect(document.querySelector(".stage-switch")).toBeNull();
  expect(RIG_LAYOUT.rig).not.toBeNull();
  receive(RIG_LAYOUT);
  const view = screen.getByRole("radiogroup", { name: "Stage view" });
  await expect.element(view).toBeInTheDocument();
  await expect.element(view.getByRole("radio", { name: "2D" })).toBeChecked();
  receive({ ...RIG_LAYOUT, rig: null });
  await expect.element(view).not.toBeInTheDocument();
});
