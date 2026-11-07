# A5. Current stack and libraries (Explore agent, Sonnet, 2026-10-22)

Brief: Oct 2026 versions and choices for the 3D frontend, toolchain, Python modeling, units and
math, extensibility, realtime transport, and testing.

**Research report, 2026-10-22.** Versions come from the npm registry `/latest` endpoints and PyPI pages fetched today unless another source is named. I did not edit anything.

**1. 3D frontend**
- **Versions and peers.**
  - @react-three/fiber 9.8.2 is latest. Its peers are react `>=19 <19.4` and three `>=0.156` (https://registry.npmjs.org/@react-three/fiber/latest). GitHub lists the 9.8.2 release on 2026-10-15 and a v10.0.0-alpha.6 on 2026-10-17 (https://api.github.com/repos/pmndrs/react-three-fiber/releases).
  - @react-three/drei 10.7.9 is latest. Its peers are react `^19`, three `>=0.159` and fiber `^9` (https://registry.npmjs.org/@react-three/drei/latest). GitHub shows 10.7.9 on 2026-09-25 and v11.0.0-alpha.7 on 2026-09-05 (https://api.github.com/repos/pmndrs/drei/releases).
  - three is 0.186.1 on npm (https://registry.npmjs.org/three/latest).
- **Maintenance.** Both libraries are actively released. Fiber v10 and drei v11 are in alpha, so a major bump is coming (inference: pin `^9` and `^10`).
- **drei helpers.** I could not confirm that TransformControls, OrbitControls, Instances, Merged or Html exist in 10.7.9, because my GitHub file lookup returned 404. "Not found" for per-helper verification. They are long-standing drei exports in my background knowledge, which is unverified for 10.7.9.
- **R3F against vanilla three.** This is an inference.
  - R3F fits the sister projects' React and zustand stack.
  - Vanilla three avoids the fiber v10 and drei v11 churn.
  - Streaming 30 fps LED colors is best written imperatively into an InstancedMesh color attribute in either approach, not through React state.
  - Pick R3F if the inspector and tools are React-heavy.
- **Undo/redo.** zundo 2.3.0 supports zustand `^4.3 || ^5` (https://registry.npmjs.org/zundo/latest). Its latest commit is 2025-04-29 (https://api.github.com/repos/charkour/zundo/commits), which is older than 12 months. It is stable but quiet. The alternative is a hand-rolled command stack, which is an inference.
- **Panels.** leva 0.10.1 supports React 18 and 19 (https://registry.npmjs.org/leva/latest). Its latest commit is 2025-11-08, so about 11 months old and borderline (https://api.github.com/repos/pmndrs/leva/commits). A numeric inspector is simple enough to build with plain Tailwind inputs (inference). tweakpane is at 4.0.5 (https://registry.npmjs.org/tweakpane/latest). I did not check its date.

**2. Toolchain**
- **Vite** is 8.3.5 and depends on `rolldown ~1.2.14`, so Rolldown is now the default bundler. It requires Node `^20.19 || >=22.12` (https://registry.npmjs.org/vite/latest).
- **TypeScript** is 7.0.2 on `latest` (https://registry.npmjs.org/typescript/latest).
  - 7.0 is the Go-native compiler. Dates are conflicting (July 8 or 9, 2026) per https://gihyo.jp/article/2026/07/typescript-7-0 and https://www.devclass.com/development/2026/07/10/speedier-type-checks-in-typescript-70-as-first-stable-go-release-ships/5269206.
  - `strict` is on by default.
  - The stable programmatic API is not in 7.0 and is expected in 7.1 (secondary reports only). Tools that need it should stay on TypeScript 6.
  - I did not verify that Vitest, Biome or orval work with TypeScript 7.
- **Tailwind** is 4.3.3 (https://registry.npmjs.org/tailwindcss/latest).
- **Biome** is 2.6.2 (https://registry.npmjs.org/@biomejs/biome/latest).
- **Vitest** is 5.0.5, with a vite peer of `^6.4 || ^7 || ^8` (https://registry.npmjs.org/vitest/latest).
- **Playwright** (`@playwright/test`) is 1.64.1 (https://registry.npmjs.org/@playwright/test/latest).
- **zustand** is 5.0.16 (https://registry.npmjs.org/zustand/latest).

**3. Python modeling and type sharing**
- **pydantic.** The changelog inside the PyPI JSON shows v2.14.1 dated 2026-10-11 (https://pypi.org/pypi/pydantic/json). That is a changelog date, not an upload time. Discriminated unions and `model_json_schema()` are built in (background knowledge, not re-verified today).
- **msgspec** is 0.22.0, released 2026-09-29 (https://pypi.org/project/msgspec/). The docs page I tried for JSON Schema returned 404. Tagged unions and `msgspec.json.schema` come from background knowledge, so label them unverified.
- **cattrs** is 26.2.1, released 2026-09-26 (https://api.github.com/repos/python-attrs/cattrs/releases). I did not verify its JSON Schema story. attrs and cattrs have no built-in JSON Schema export (inference).
- **Recommendation (inference).** Use pydantic. It covers validation, unions and schema in one tool, and it matches FastAPI in the sister projects.
- **Sharing types.**
  - orval is 8.44.0 (https://registry.npmjs.org/orval/latest) and generates from OpenAPI. json-schema-to-typescript is 16.0.0 (https://registry.npmjs.org/json-schema-to-typescript/latest).
  - Because FastAPI emits OpenAPI containing the pydantic models, orval is the single path the sister projects already use (inference).
  - Use json-schema-to-typescript only to type the standalone file format (inference). I did not research quicktype.

**4. Units and 3D math**
- **pint** is 0.26.2, released 2026-10-19 (https://pypi.org/project/pint/). **scipy** is 1.18.1, released 2026-08-21, and requires Python 3.12 or later (https://pypi.org/project/scipy/). This conflicts with a "Python 3.11+" project floor.
- **Recommendation (inference).**
  - Use plain SI floats with suffixes such as `_m` and `_w`. Pint adds overhead in the per-frame path.
  - Write numpy-only quaternions, because scipy drops 3.11.
  - Store quaternions as xyzw, which matches three.js `Quaternion.toArray()` and scipy's order. Avoid Euler in the file format. If Euler is needed, three's default order is XYZ (background knowledge).

**5. Extensibility**
- I found no 2026-specific source for this question. This is all inference: ship catalogs as JSON or TOML validated by pydantic, with a `kind` discriminator. Add `importlib.metadata` entry points later only if third-party packages need to register code, such as chipset encoders.

**6. Realtime transport**
- **websockets** is 17.3, released 2026-10-19 (https://websockets.readthedocs.io/en/stable/project/changelog.html).
  - The sync server added `broadcast()` and `Server.connections` in 17.0.
  - 17.3 switched the sync server to non-blocking reads.
  - 17.3 also tested compatibility with uvloop.
- **Options.**
  - Your threaded design could keep the sync server unchanged. I did not confirm its per-connection limits at tens of clients.
  - FastAPI plus uvicorn would match the sister projects. This is an inference. I did not fetch FastAPI or uvicorn versions or Starlette websocket docs.
- **Thread bridge.** Per-session render threads call `loop.call_soon_threadsafe(queue.put_nowait, frame)`, with a small drop-oldest queue per socket. This is my own suggestion from asyncio knowledge, not a sourced claim.
- **WebTransport browser support.**
  - Safari 26.4 shipped it, with interoperability since 2026-03-24 (https://webrtc.ventures/2026/04/webtransport-is-now-baseline-what-it-means-for-real-time-media/). This comes from secondary sources, and I did not see caniuse directly.
  - Some pages still call Safari support missing (https://www.videosdk.live/developer-hub/webtransport/safari-webtransport). They are stale.
- **WebTransport on fly.io.**
  - A forum post says Fly Proxy terminates TLS and does not forward QUIC, HTTP/3 or WebTransport. The workaround is to terminate TLS yourself on UDP (https://community.fly.io/t/configuring-webtransport-server-via-a-gateway-setting-up-certs/27518).
  - I could not confirm dates. The related thread is old (https://community.fly.io/t/plans-to-support-quic-and-http3/1899).
  - I found no official Fly docs, so this is "not found" for official support.
- **Verdict (inference).** Not worth it. WebSockets at 40 KB and 30 fps are about 1.2 MB/s per client, which is fine.

**7. Testing**
- **Hypothesis** is 6.170.8 (https://pypi.org/pypi/hypothesis/json). I did not find its release date.
- **Playwright and Vitest** versions are in section 2.
- **Playwright screenshots of WebGL canvases.** I did not research this. My suggestion (inference) is to fix the camera, size and seed, use software GL (SwiftShader) in CI, and set a tolerant `maxDiffPixelRatio`. Prefer asserting scene-graph state through a test hook.
- **Vitest** should cover the pure logic: geometry, array tools and the undo store.

**Recommended stack**

| Layer | Choice | Version |
|---|---|---|
| 3D | three, @react-three/fiber, @react-three/drei | 0.186.1, 9.8.2, 10.7.9 |
| State and undo | zustand, zundo (or a custom command stack) | 5.0.16, 2.3.0 |
| Inspector | plain Tailwind inputs (leva is optional) | n/a, 0.10.1 |
| Build and style | Vite, TypeScript, Tailwind | 8.3.5, 7.0.2 (6 if tool issues), 4.3.3 |
| Lint and test | Biome, Vitest, Playwright | 2.6.2, 5.0.5, 1.64.1 |
| Models | pydantic, orval | 2.14.x, 8.44.0 |
| Math | numpy quaternions (xyzw), SI floats | n/a |
| Transport | websockets 17.3 or FastAPI/uvicorn WebSockets | 17.3 |
| Tests | Hypothesis | 6.170.8 |

## Sources

- https://registry.npmjs.org/@react-three/fiber/latest
- https://api.github.com/repos/pmndrs/react-three-fiber/releases
- https://registry.npmjs.org/@react-three/drei/latest
- https://api.github.com/repos/pmndrs/drei/releases
- https://registry.npmjs.org/three/latest
- https://registry.npmjs.org/zundo/latest
- https://api.github.com/repos/charkour/zundo/commits
- https://registry.npmjs.org/leva/latest
- https://api.github.com/repos/pmndrs/leva/commits
- https://registry.npmjs.org/tweakpane/latest
- https://registry.npmjs.org/vite/latest
- https://registry.npmjs.org/typescript/latest
- https://gihyo.jp/article/2026/07/typescript-7-0
- https://www.devclass.com/development/2026/07/10/speedier-type-checks-in-typescript-70-as-first-stable-go-release-ships/5269206
- https://registry.npmjs.org/tailwindcss/latest
- https://registry.npmjs.org/@biomejs/biome/latest
- https://registry.npmjs.org/vitest/latest
- https://registry.npmjs.org/@playwright/test/latest
- https://registry.npmjs.org/zustand/latest
- https://pypi.org/pypi/pydantic/json
- https://pypi.org/project/msgspec/
- https://api.github.com/repos/python-attrs/cattrs/releases
- https://registry.npmjs.org/orval/latest
- https://registry.npmjs.org/json-schema-to-typescript/latest
- https://pypi.org/project/pint/
- https://pypi.org/project/scipy/
- https://websockets.readthedocs.io/en/stable/project/changelog.html
- https://webrtc.ventures/2026/04/webtransport-is-now-baseline-what-it-means-for-real-time-media/
- https://www.videosdk.live/developer-hub/webtransport/safari-webtransport
- https://community.fly.io/t/configuring-webtransport-server-via-a-gateway-setting-up-certs/27518
- https://community.fly.io/t/plans-to-support-quic-and-http3/1899
- https://pypi.org/pypi/hypothesis/json
