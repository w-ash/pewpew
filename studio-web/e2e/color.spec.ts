import { expect, test } from "@playwright/test";

interface ColorCheck {
  expected: number[][];
  pixels: number[][];
  nearest: number[][];
}

test("display-ready bytes reach the screen unchanged at texel centers", async ({
  page,
}) => {
  await page.goto("/e2e/fixtures/color.html");
  const check = (await page
    .waitForFunction(
      () => (window as unknown as { colorCheck?: unknown }).colorCheck,
    )
    .then((h) => h.jsonValue())) as ColorCheck;
  // pixel_nearest fetches the texel itself: exact.
  expect(check.nearest).toEqual(check.expected);
  // pixels filters linearly; the fixture puts texel centers on pixel
  // centers, and one step is left for GPU filter precision. Encoding twice
  // would turn 128 into about 186.
  check.pixels.forEach((rgb, i) => {
    rgb.forEach((v, c) => {
      expect(Math.abs(v - check.expected[i][c])).toBeLessThanOrEqual(1);
    });
  });
});
