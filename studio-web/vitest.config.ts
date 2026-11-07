import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config.ts";

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      // Disables Node 25's native Web Storage so jsdom's localStorage serves
      // tests; MSW probes the global at import.
      execArgv: ["--no-experimental-webstorage"],
      globals: true,
      setupFiles: ["./src/test/setup.ts"],
      include: ["src/**/*.test.{ts,tsx}"],
      exclude: ["src/api/generated/**"],
    },
  }),
);
