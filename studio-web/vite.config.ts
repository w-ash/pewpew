import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

const BACKEND = "http://127.0.0.1:8000";

/** Serve msw's service worker in `--mode mock` dev only, so it never reaches dist/. */
function mockServiceWorker(): Plugin {
  const require = createRequire(import.meta.url);
  return {
    name: "pewpew-mock-service-worker",
    apply: "serve",
    configureServer(server) {
      if (server.config.mode !== "mock") return;
      const file = require.resolve("msw/mockServiceWorker.js");
      server.middlewares.use("/mockServiceWorker.js", (_req, res) => {
        res.setHeader("Content-Type", "text/javascript");
        res.end(readFileSync(file));
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), mockServiceWorker()],
  resolve: {
    tsconfigPaths: true,
  },
  server: {
    port: 5173,
    // The default arrangement is imported from the rig package's examples.
    fs: { allow: [".", "../src/pewpew/rig/examples"] },
    proxy: {
      "/api": { target: BACKEND, changeOrigin: true },
      "/ws": { target: BACKEND, ws: true, changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    // The three.js chunk is about 1 MB minified (277 kB gzipped) and loads once.
    chunkSizeWarningLimit: 1100,
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: "three-vendor",
              test: /[\\/]node_modules[\\/](three|three-stdlib|@react-three)[\\/]/,
              priority: 30,
            },
            {
              name: "react-vendor",
              test: /[\\/]node_modules[\\/](react|react-dom|scheduler|@tanstack|zustand)[\\/]/,
              priority: 20,
            },
          ],
        },
      },
    },
  },
});
