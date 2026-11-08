import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import babel from "@rolldown/plugin-babel";
import react, { reactCompilerPreset } from "@vitejs/plugin-react";
import { playwright } from "@vitest/browser-playwright";
import { defineConfig, type Plugin, type UserConfig } from "vite";
import type { BrowserCommand } from "vitest/node";
import { upgradeAllowed } from "./dev-origin.ts";

// Two pages from one source tree. The default mode is the engine's control page
// (index.html), built into src/pewpew/sinks/web: the page and its hashed files,
// which the engine serves (src/pewpew/sinks/preview.py). The mode `studio` is
// the hosted studio (studio.html), built into dist/studio.

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

// The licenses of every bundled package, in every file of the build, from
// Vite's `build.license`, then the fonts', moved into the page as a comment: the
// page ships with every file it loads. The minifier drops the packages' own
// license headers.
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

/** The files the engine serves beside the page (`files.json`, read by
 * `web_files()` in src/pewpew/sinks/preview.py): every file of the build but
 * the page itself and the manifest, sorted. */
const FILES = "files.json";
const MANIFEST = "manifest.json";

function servedFiles(): Plugin {
  return {
    name: "pewpew-served-files",
    apply: "build",
    generateBundle: {
      order: "post",
      handler(_, bundle) {
        const files = Object.keys(bundle).filter((name) => name !== "index.html" && name !== MANIFEST && name !== LICENSES).sort();
        this.emitFile({ type: "asset", fileName: FILES, source: `${JSON.stringify(files, null, 2)}\n` });
      },
    },
  };
}

/** The Console's 3D view (src/rig3d), three.js, and the packages only they
 * use, in one file loaded only when the stage first shows 3D. The group takes
 * none of the other modules they import (`includeDependenciesRecursively:
 * false`), so React and the page's own modules stay with the page
 * (https://rolldown.rs/reference/TypeAlias.CodeSplittingGroup); it names
 * @react-three's own dependencies, which would otherwise make a second 3D
 * file that imports the first and is imported by it. */
const CONSOLE_3D = new RegExp(
  String.raw`[\/]node_modules[\/](three|three-stdlib|@react-three[\/][^\/]+|its-fine|suspend-react|react-use-measure|@babel[\/]runtime)[\/]` +
    String.raw`|[\/]src[\/]rig3d[\/]`,
);

/** The Console's layout editor and report (src/arrange), the page's modules only they use (design/Field,
 * params/NumberField), and their store's package, zustand (which @react-three uses too), in one file
 * loaded when the layout panel, the report or the 3D view first opens: the 3D view edits through the
 * same store. A module named here that the page comes to use loads with the page, over its budget
 * (tests/test_page_build.py). */
const CONSOLE_RIG = new RegExp(
  String.raw`[\/]node_modules[\/](zustand|use-sync-external-store)[\/]` +
    String.raw`|[\/]src[\/](arrange[\/]|design[\/]Field\.tsx|params[\/]NumberField\.tsx)`,
);

/** Every other module the page imports, in one file the page loads at once. Two files loaded on demand
 * that import the same modules of the page would otherwise get those modules split into a file of their
 * own, which costs the page about 4 kB gzipped in the names the two files trade (Rolldown 1.2). The
 * page's entry is then only its `main.tsx`. */
const PAGE = /[\\/](src|node_modules)[\\/]/;

/** The studio's page: served for `/` and a share link `/a/<id>` in dev, and
 * built as index.html, the name the studio server serves (studio/app.py). */
function studioPage(): Plugin {
  return {
    name: "pewpew-studio-page",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        const path = req.url?.split("?")[0];
        if (path === "/" || path?.startsWith("/a/")) req.url = "/studio.html";
        next();
      });
    },
    generateBundle: {
      order: "post",
      handler(_, bundle) {
        const page = bundle["studio.html"];
        if (page?.type !== "asset") throw new Error("no studio page");
        delete bundle["studio.html"];
        this.emitFile({ type: "asset", fileName: "index.html", source: page.source });
      },
    },
  };
}

// Moves the pointer off the page, so it lies over nothing a test renders (test/setup.ts).
const pointerAway: BrowserCommand = ({ page }) => page.mouse.move(-1, -1);

// A component the React Compiler cannot compile fails the build, so none
// silently goes without memoization.
const compiledReact = () => [react(), babel({ presets: [reactCompilerPreset({ panicThreshold: "all_errors" })] })];

/** The hosted studio: a single-page app with its three.js chunk apart, beside a studio server. */
function studio(): UserConfig {
  const server = "http://127.0.0.1:8000";
  return {
    plugins: [compiledReact(), studioPage()],
    server: {
      host: "127.0.0.1",
      port: 5173,
      // The default arrangement is imported from the rig package's examples.
      fs: { allow: [".", "../src/pewpew/rig/examples"] },
      proxy: { "/api": { target: server, changeOrigin: true }, "/ws": { target: server, ws: true, changeOrigin: true } },
    },
    build: {
      outDir: "dist/studio",
      rolldownOptions: {
        input: "studio.html",
        output: {
          codeSplitting: {
            groups: [
              { name: "three-vendor", test: /[\\/]node_modules[\\/](three|three-stdlib|@react-three)[\\/]/, priority: 30 },
              { name: "react-vendor", test: /[\\/]node_modules[\\/](react|react-dom|scheduler|@tanstack|zustand)[\\/]/, priority: 20 },
            ],
          },
        },
      },
      // The three.js chunk is about 1 MB minified (277 kB gzipped) and loads once.
      chunkSizeWarningLimit: 1100,
    },
  };
}

export default defineConfig(({ command, mode }) => {
  if (mode === "studio") return studio();
  // The dev server proxies to a running engine, e.g.
  // PEWPEW_ENGINE=http://127.0.0.1:52011 pnpm dev
  const engine = process.env.PEWPEW_ENGINE;
  if (command === "serve" && mode === "development" && !engine) {
    throw new Error("set PEWPEW_ENGINE to the engine's preview URL, e.g. http://127.0.0.1:52011");
  }
  return {
    plugins: [compiledReact(), buildStamp(), inlineLicenses(), servedFiles()],
    // Every dependency found up front: one found mid-run reloads the test page
    // with a second copy of React.
    optimizeDeps: { entries: ["src/**/*.{ts,tsx}", "test/**/*.{ts,tsx}"] },
    build: {
      outDir: "../src/pewpew/sinks/web",
      // The folder holds only the build: a file of an older build is not left to be served.
      emptyOutDir: true,
      // Which files each chunk imports, for tests/test_page_build.py (https://vite.dev/guide/backend-integration).
      manifest: MANIFEST,
      license: { fileName: LICENSES },
      // Every asset (the fonts) goes inline, and one stylesheet holds every chunk's styles: the page fetches
      // only scripts and that stylesheet.
      assetsInlineLimit: () => true,
      cssCodeSplit: false,
      // Every browser the page supports has module preload.
      modulePreload: { polyfill: false },
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [
              { name: "console-3d", test: CONSOLE_3D, includeDependenciesRecursively: false, priority: 2 },
              { name: "console-rig", test: CONSOLE_RIG, includeDependenciesRecursively: false, priority: 2 },
              { name: "page", test: PAGE, includeDependenciesRecursively: false, priority: 0 },
            ],
          },
        },
      },
      // The 3D chunk is about 1 MB minified and loads once, on demand.
      chunkSizeWarningLimit: 1100,
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
            "/parts.json": { target: engine, changeOrigin: true },
            "/assembly": { target: engine, changeOrigin: true },
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
