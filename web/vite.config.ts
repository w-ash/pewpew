import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import babel from "@rolldown/plugin-babel";
import react, { reactCompilerPreset } from "@vitejs/plugin-react";
import { playwright } from "@vitest/browser-playwright";
import { defineConfig, type Plugin } from "vite";
import type { BrowserCommand } from "vitest/node";
import { viteSingleFile } from "vite-plugin-singlefile";
import { upgradeAllowed } from "./dev-origin.ts";

// The build stamp, from the same function tests/test_page_build.py checks.
function buildStamp(): Plugin {
  return {
    name: "pewpew-build-stamp",
    apply: "build",
    transformIndexHtml() {
      const hash = execFileSync("python3", ["../tools/webhash.py"], { encoding: "utf8" }).trim();
      return [{ tag: "meta", attrs: { name: "pewpew-build", content: hash }, injectTo: "head" }];
    },
  };
}

const LICENSES = "licenses.md";
// The fonts' copyright lines and licence, which OFL §2 asks every copy to carry (tools/fonts.py).
const FONT_LICENSE = new URL("./src/design/fonts/OFL.txt", import.meta.url);

// The licenses of every bundled package, from Vite's `build.license`, then the
// fonts', moved into the page as a comment: the one file is all that ships. The
// minifier drops the packages' own license headers.
function inlineLicenses(): Plugin {
  return {
    name: "pewpew-inline-licenses",
    apply: "build",
    generateBundle: {
      order: "post",
      handler(_, bundle) {
        const licenses = bundle[LICENSES], page = bundle["index.html"];
        if (licenses?.type !== "asset" || page?.type !== "asset") throw new Error("no licenses or no page to put them in");
        const fonts = `## Martian Grotesk and Martian Mono (OFL-1.1)\n\n${readFileSync(FONT_LICENSE, "utf8")}`;
        const text = `${String(licenses.source).trimEnd()}\n\n${fonts}`.replace(/-(?=-)/g, "- "); // no "--" inside a comment
        page.source = String(page.source).replace("</html>", `<!--\n${text}\n-->\n</html>`);
        delete bundle[LICENSES];
      },
    },
  };
}

// Moves the pointer off the page, so it lies over nothing a test renders (test/setup.ts).
const pointerAway: BrowserCommand = ({ page }) => page.mouse.move(-1, -1);

export default defineConfig(({ command, mode }) => {
  // The dev server proxies to a running engine, e.g.
  // PEWPEW_ENGINE=http://127.0.0.1:52011 pnpm dev
  const engine = process.env.PEWPEW_ENGINE;
  if (command === "serve" && mode === "development" && !engine) {
    throw new Error("set PEWPEW_ENGINE to the engine's preview URL, e.g. http://127.0.0.1:52011");
  }
  return {
    // A component the React Compiler cannot compile fails the build, so none
    // silently goes without memoization.
    plugins: [react(), babel({ presets: [reactCompilerPreset({ panicThreshold: "all_errors" })] }), viteSingleFile(), buildStamp(), inlineLicenses()],
    // Every dependency found up front: one found mid-run reloads the test page
    // with a second copy of React.
    optimizeDeps: { entries: ["src/**/*.{ts,tsx}", "test/**/*.{ts,tsx}"] },
    build: {
      outDir: "../src/pewpew/sinks/web",
      emptyOutDir: false,
      license: { fileName: LICENSES },
      // One file and no chunks: nothing to preload.
      modulePreload: { polyfill: false },
    },
    server: {
      host: "127.0.0.1",
      proxy: engine
        ? {
            "/ws": {
              target: engine,
              ws: true,
              changeOrigin: true,
              rewriteWsOrigin: true,
              // An upgrade from another origin is answered 404 and never reaches the engine.
              bypass: (req, res) => (res || upgradeAllowed(req.headers.host, req.headers.origin) ? undefined : false),
            },
            "/plan": { target: engine, changeOrigin: true },
          }
        : undefined,
    },
    test: {
      include: ["test/**/*.test.{ts,tsx}"],
      setupFiles: ["test/setup.ts"],
      browser: {
        enabled: true,
        headless: true,
        provider: playwright(),
        instances: [{ browser: "chromium" }, { browser: "webkit" }],
        commands: { pointerAway },
      },
    },
  };
});
