import { defineConfig } from "@playwright/test";

// The studio's end-to-end tests, against the studio page in mock mode.
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
    command: `pnpm exec vite --mode mock --port ${PORT} --strictPort --host 127.0.0.1`,
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
