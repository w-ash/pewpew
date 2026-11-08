import { tmpdir } from "node:os";
import { join } from "node:path";
import { defineConfig } from "@playwright/test";

// The end-to-end tests, against the studio's dev server, which proxies /api and /ws to the
// studio backend on :8000. Both start here.
const PORT = 5179;
const BACKEND_PORT = 8000;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    browserName: "chromium",
  },
  webServer: [
    {
      command: `uv run python -m pewpew studio --port ${BACKEND_PORT} --db ${join(tmpdir(), "pewpew-e2e-studio.sqlite3")}`,
      cwd: "..",
      url: `http://127.0.0.1:${BACKEND_PORT}/api/looks`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `pnpm exec vite --mode studio --port ${PORT} --strictPort --host 127.0.0.1`,
      url: `http://127.0.0.1:${PORT}`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
