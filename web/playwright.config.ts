import { defineConfig } from "@playwright/test";

// The end-to-end tests, against the studio's dev server.
const PORT = 5179;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    browserName: "chromium",
  },
  webServer: {
    command: `pnpm exec vite --mode studio --port ${PORT} --strictPort --host 127.0.0.1`,
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
