# ws4 simplify pass: studio web app

Four review passes (reuse, simplification, efficiency, altitude) over `web/`. Gates `pnpm check`, `pnpm test`, `pnpm e2e` pass, including `e2e/color.spec.ts`. No behavior, color-path or wire-protocol change.

## Changes (paths under `web/src/`)

- `viewer/Stage.tsx:253-259`: camera-view buttons render the local `ToggleButton` instead of copying its markup.
- `viewer/ledTexture.ts:77`, `viewer/Rig.tsx:78,98`: new `uploadFrame` holds the length guard, fill and `needsUpdate`; both call sites used the same code. The fill itself is unchanged.
- `mocks/compile.ts:29`: mock `poseMatrix` delegates to `editor/pose.ts` `poseMatrix` with `IDENTITY_POSE` defaults.
- `mocks/frames.ts:7`: imports `MOCK_PIXELS_PER_BAR`; local duplicate constant removed.
- `mocks/handlers.ts:41`: `compileOr422` replaces two identical try/catch blocks.
- `mocks/session.ts:18`: `sessionLink` no longer exported (no outside user).
- `session/client.ts:15,47,65`: `onFrame` typed with `Frame` from `./protocol` instead of `Parameters<typeof frameBus.push>[0]`.
- `panels/ArrangementPanel.tsx:65-127`: dropped the `edit` alias for `commit` in `ArrangementPanel`; `addGroup` shared by `addRing` and `addArray`. The inner editor still takes its `edit` prop.
- `panels/ReportPanel.tsx:148,156,186`: removed the unread `depth` prop of `ReportNode`.
- `panels/ui.tsx:15-39`: removed `Button` props `pressed`, `className`, `type` (no callers).
- `store/doc.ts:58`: removed unused `useArrangement`.
- `editor/arrangement.ts:208`: removed an orphan docstring above `swapEnds` that described `flip`.

## Left alone

- Per-frame path: reviewed clean. Frames go through `frameBus` into the texture in `useFrame`; React sees `t` at most every 250 ms in `StageStatus`.
- Mock store split, hand-written mock server vs orval mocks, `api/endpoints.ts`/`types.ts` stand-ins for the generated client, mock-mode Vite plugin: depend on ws3 landing or are design decisions, not cleanups.
- `SessionClient` injection points (`store`, `visibility`): tests use them; removing means rewriting tests.
- Shared `createVersioned` for `frameBus`/`dragPreview`, `share/route.ts` for the `/a/<id>` path: new modules for modest gain.
- `arrangement.ts` `mapEntity` refactor (four functions), `instances.ts` host/attachment loop merge and `End` type: larger edits in tested core logic; risk outweighs gain.
- Efficiency items (`Rig.tsx` drag subarrays, `hostAxis` bounding box memo, `Stage` inline callbacks, `assembliesFor` lookups, `Gizmo` Matrix4): none on the color or per-frame path; per-drag or per-compile only.
- `rigBounds` via `Box3`/`Sphere`: modest saving, medium confidence.
- Unused `Sourced`/`PatternInfo` in `api/types.ts`: mirror the contract types.
- Unused `store/session.ts` `catalogDigest`/`boundIssues`: mirror `bound` fields from the wire contract.
- Wider unexports (`PoseInspector`, `shareUrl`, `api/types.ts` names): public-surface only, no cost.
- `Stage.tsx:145` possible double sRGB conversion of the accent color: not verified, outside the texture path; worth a separate check.
