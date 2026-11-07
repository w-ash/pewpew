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
  // 48 bars × 25.6 W = 1228.8 W; RGB through Accurate auto-white reaches half, 614.4 W; × 18.4% = 113.0 W.
  await expect(page.getByTestId("report-capped")).toContainText("614.4 W");
  const brightness = page.getByLabel(/Max brightness/);
  await brightness.fill("18.4");
  await expect(page.getByTestId("report-capped")).toContainText("113.0 W");
  await page.getByLabel(/Max watts/).fill("100");
  await expect(page.getByTestId("report-capped")).toContainText("100.0 W");

  await page.getByRole("tab", { name: "Share" }).click();
  await page.getByRole("button", { name: "Save and get a link" }).click();
  const link = await page.getByTestId("share-link").inputValue();
  await page.goto(new URL(link).pathname);
  await page.getByRole("tab", { name: "Report" }).click();
  await expect(page.getByLabel(/Max watts/)).toHaveValue("100");
  await expect(page.getByLabel(/Max brightness/)).toHaveValue("18.4");
  await expect(page.getByTestId("report-capped")).toContainText("100.0 W");
});
