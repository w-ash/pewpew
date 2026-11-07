import { expect, test } from "@playwright/test";

test("the power cap resizes the report and a share link keeps it", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByTestId("stage-status")).toContainText(
    "live · 3072 px",
    { timeout: 15_000 },
  );
  await page.getByRole("tab", { name: "Report" }).click();
  // 48 bars × 25.6 W = 1228.8 W; RGB through Accurate auto-white reaches half, 614.4 W; × 20% = 122.9 W.
  await expect(page.getByTestId("report-capped")).toContainText("614.4 W");
  const entry = (name: string) => page.getByRole("spinbutton", { name });
  await entry("Max brightness").fill("20");
  await entry("Max brightness").press("Enter");
  await expect(page.getByTestId("report-capped")).toContainText("122.9 W");
  await page.getByRole("switch", { name: "Cap the watts" }).check();
  await entry("Max watts").fill("100");
  await entry("Max watts").press("Enter");
  await expect(page.getByTestId("report-capped")).toContainText("100.0 W");

  await page.getByRole("tab", { name: "Share" }).click();
  await page.getByRole("button", { name: "Save and get a link" }).click();
  const link = await page.getByTestId("share-link").inputValue();
  await page.goto(new URL(link).pathname);
  await page.getByRole("tab", { name: "Report" }).click();
  await expect(entry("Max watts")).toHaveValue("100.0");
  await expect(entry("Max brightness")).toHaveValue("20");
  await expect(page.getByTestId("report-capped")).toContainText("100.0 W");
});
