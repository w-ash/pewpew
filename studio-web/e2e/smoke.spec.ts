import { expect, type Page, test } from "@playwright/test";

/** Share of canvas pixels that are lit and saturated, read back through a 2D canvas. */
async function litFraction(page: Page): Promise<number> {
  const png = await page.locator("canvas").first().screenshot();
  return page.evaluate(async (b64) => {
    const img = new Image();
    img.src = `data:image/png;base64,${b64}`;
    await img.decode();
    const c = document.createElement("canvas");
    c.width = img.width;
    c.height = img.height;
    const ctx = c.getContext("2d");
    if (!ctx) return 0;
    ctx.drawImage(img, 0, 0);
    const { data } = ctx.getImageData(0, 0, c.width, c.height);
    let lit = 0;
    for (let i = 0; i < data.length; i += 4) {
      const hi = Math.max(data[i], data[i + 1], data[i + 2]);
      const lo = Math.min(data[i], data[i + 1], data[i + 2]);
      if (hi > 120 && hi - lo > 80) lit++;
    }
    return lit / (data.length / 4);
  }, png.toString("base64"));
}

test("loads the golden rings against the mock and streams frames onto them", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });

  await page.goto("/");
  await expect(page.getByTestId("entity-list")).toContainText("inner");
  await expect(page.getByTestId("entity-list")).toContainText("outer");
  await expect(page.getByTestId("stage-status")).toContainText(
    "live · 3072 px",
    { timeout: 15_000 },
  );
  await expect(page.getByTestId("stage-status")).toContainText("48 fixtures");

  await expect
    .poll(() => litFraction(page), { timeout: 10_000 })
    .toBeGreaterThan(0.01);

  await page.getByRole("button", { name: /^inner/ }).click();
  await expect(page.getByRole("region", { name: "Ring" })).toBeVisible();

  await page.getByRole("tab", { name: "Effect" }).click();
  const controls = page.getByRole("region", { name: "Pattern controls" });
  await expect(controls).toContainText("Speed");
  // A pattern with a color, an int, a bool and a choice: each control sends its kind.
  await page.getByLabel("Running on the server").selectOption("pulse");
  await expect(controls.getByLabel("Shape")).toBeVisible();
  await controls.getByLabel("Shape").selectOption("flat");
  await controls.getByLabel("Color").fill("#ff0000");
  await controls.getByRole("switch", { name: "Invert" }).click();
  await expect(controls.getByLabel("Shape")).toHaveValue("flat");
  await expect(controls.getByLabel("Color")).toHaveValue("#ff0000");

  await page.getByRole("tab", { name: "Report" }).click();
  await page.locator("summary", { hasText: "Warnings" }).click();
  await expect(page.locator('[data-level="warning"]').first()).toBeVisible();
  await expect(page.getByTestId("report-watts")).toContainText("W");

  expect(errors).toEqual([]);
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

  test("controls are at least 44 px and fields 16 px, so iOS does not zoom", async ({
    page,
  }) => {
    // Playwright's touch emulation leaves the pointer fine; a phone's is coarse.
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Emulation.setEmulatedMedia", {
      features: [{ name: "pointer", value: "coarse" }],
    });
    await page.goto("/");
    await expect(page.getByTestId("entity-list")).toContainText("inner");
    await page.getByRole("button", { name: /^inner/ }).click();
    // A control under a finger is drawn smaller and answers on a ::before
    // that reaches past its edges (web/src/design/controls.css).
    const heights = await page
      .locator("button:visible, [role=tab]:visible")
      .evaluateAll((els) =>
        els.map((e) =>
          Math.max(
            e.getBoundingClientRect().height,
            Number.parseFloat(getComputedStyle(e, "::before").height) || 0,
          ),
        ),
      );
    expect(heights.length).toBeGreaterThan(5);
    expect(Math.min(...heights)).toBeGreaterThanOrEqual(44);
    const fonts = await page
      .locator("input:visible, select:visible")
      .evaluateAll((els) =>
        els.map((e) => Number.parseFloat(getComputedStyle(e).fontSize)),
      );
    expect(fonts.length).toBeGreaterThan(3);
    expect(Math.min(...fonts)).toBeGreaterThanOrEqual(16);
  });
});
