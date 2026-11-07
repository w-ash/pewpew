# A2. three.js LED viewer and editor (Explore agent, default model, 2026-10-22)

Brief: current three.js release and no-bundler setup; driving per-LED colors on many bars; passing
display-ready sRGB bytes unchanged; editing UX in lighting tools; phone constraints.

I found answers for most of the questions. The main gaps are vendor docs for xLights snapping, MadMapper, Depence, Vectorworks Vision and Pixelblaze, all marked "not found" below. "Old" means the source is more than about 12 months old.

**1. three.js as of October 2026**
- **Current release:** r186, released 24 Sep 2026, with no r187 tag yet ([github.com/mrdoob/three.js/tags](https://github.com/mrdoob/three.js/tags)). On npm, `three` is 0.186.1 under the MIT license ([registry.npmjs.org/three/latest](https://registry.npmjs.org/three/latest); the [LICENSE file](https://github.com/mrdoob/three.js/blob/r186/LICENSE) reads "© 2010-2026").
- **No-bundler setup:** an import map with `"three": ".../build/three.module.js"` and `"three/addons/": ".../examples/jsm/"`. The manual says to import every file from the same version and the same source ([threejs.org/manual/pages/installation.html](https://threejs.org/manual/pages/installation.html), undated). *Inference:* to vendor, point both entries at local copies of `build/` and `examples/jsm/`.
- **Changes since r128** (Migration Guide, [github.com/mrdoob/three.js/wiki/Migration-Guide](https://github.com/mrdoob/three.js/wiki/Migration-Guide)):
  - r148 removed `examples/js`.
  - r152 replaced `outputEncoding` with `outputColorSpace` (default sRGB) and `texture.encoding` with `texture.colorSpace` (default NoColorSpace), and turned `ColorManagement.enabled` on by default.
  - r155 made `useLegacyLights=false` the default. *Inference:* the prototype's lights will look different.
  - r163 dropped WebGL 1.
  - r169 made TransformControls derive from `Controls`; you now call `scene.add(controls.getHelper())`.
  - r186 added `Object3D.dispose()`.
- **Renderer defaults:** the WebGLRenderer source sets `outputColorSpace = SRGBColorSpace` and `toneMapping = NoToneMapping` ([src/renderers/WebGLRenderer.js](https://github.com/mrdoob/three.js/blob/r186/src/renderers/WebGLRenderer.js#L312) at r186; `toneMapping` at [L277](https://github.com/mrdoob/three.js/blob/r186/src/renderers/WebGLRenderer.js#L277)).
- **WebGPURenderer:** the manual calls it "still in an experimental state" and says WebGLRenderer is "the recommended choice for pure WebGL 2 applications". WebGPURenderer does not support `ShaderMaterial`, `RawShaderMaterial`, `onBeforeCompile` or EffectComposer, and it falls back to WebGL 2 on its own ([threejs.org/manual/pages/webgpurenderer.html](https://threejs.org/manual/pages/webgpurenderer.html), undated).
  - Utsubo, a studio that sells WebGPU work, recommends WebGPU for new projects but says to profile first ([utsubo.com/blog/threejs-2026-what-changed](https://utsubo.com/blog/threejs-2026-what-changed), 24 Sep 2026).
  - Phone support: Chrome Android 121+ on Android 12+ with Qualcomm/ARM GPUs, and iOS 26. Firefox Android does not have it yet ([web.dev/blog/webgpu-supported-major-browsers](https://web.dev/blog/webgpu-supported-major-browsers), 25 Nov 2025). caniuse puts global support at 87.82% ([caniuse.com/webgpu](https://caniuse.com/webgpu)).
  - *Inference:* WebGLRenderer is the safe default for phones and keeps your GLSL approach.

**2. Driving per-LED colors**
- **InstancedMesh:** one draw call for many copies ([threejs.org/docs/pages/InstancedMesh.html](https://threejs.org/docs/pages/InstancedMesh.html)). `setColorAt` gives only one color per tube. Custom per-instance data needs an `InstancedBufferAttribute` plus a shader patch ([discourse.threejs.org/t/11271](https://discourse.threejs.org/t/11271), old). BatchedMesh keeps its own per-instance data in a DataTexture ([discourse.threejs.org/t/72996](https://discourse.threejs.org/t/72996), old).
- *Inference, recommended:* one InstancedMesh of a shared cylinder with a per-instance row index, and a ShaderMaterial that samples a 64×N DataTexture at (position along the axis, row). That is about 58 KB uploaded per frame for 300 tubes. Use one persistent texture and set `needsUpdate` once per frame (forum guidance, old). Per-vertex colors would need 64+ rings per tube and can't be shared across instances, so I'd rule them out.
- **DataTexture defaults:** NearestFilter for both filters, no mipmaps, `flipY=false`, `unpackAlignment=1` ([src/textures/DataTexture.js](https://github.com/mrdoob/three.js/blob/r186/src/textures/DataTexture.js#L32), defaults at [L32](https://github.com/mrdoob/three.js/blob/r186/src/textures/DataTexture.js#L32), [L60](https://github.com/mrdoob/three.js/blob/r186/src/textures/DataTexture.js#L60), [L71](https://github.com/mrdoob/three.js/blob/r186/src/textures/DataTexture.js#L71) and [L81](https://github.com/mrdoob/three.js/blob/r186/src/textures/DataTexture.js#L81)). You must set `magFilter = LinearFilter` yourself to get the diffused look.
- **Raw path (bytes reach the screen unchanged):**
  - Leave the texture at NoColorSpace (RGBFormat is fine) and use a ShaderMaterial without the `colorspace_fragment` chunk, with `toneMapped:false`.
  - The manual says ShaderMaterial "ha[s] to implement [its] own output color space conversion", while built-in materials convert automatically ([threejs.org/manual/pages/color-management.html](https://threejs.org/manual/pages/color-management.html)).
  - *Inference:* the prototype's patched MeshStandardMaterial would apply gamma a second time on r152+.
  - *Inference:* in this path the linear filtering blends the gamma-encoded values.
- **Managed path:** `SRGBColorSpace` requires RGBAFormat and UnsignedByteType; otherwise three.js logs a warning ([src/renderers/webgl/WebGLTextures.js](https://github.com/mrdoob/three.js/blob/r186/src/renderers/webgl/WebGLTextures.js#L2441-L2451)). The GPU decodes the bytes and the output stage encodes them again, so they come back unchanged (*inference*). The server's RGB bytes would need padding to RGBA (*inference*).
- **Bloom changes this:** three.js skips output conversion for ordinary render targets. OutputPass applies the sRGB transfer when `outputColorSpace` is sRGB ([examples/jsm/postprocessing/OutputPass.js](https://github.com/mrdoob/three.js/blob/r186/examples/jsm/postprocessing/OutputPass.js#L97-L104)). *Inference:* if you add bloom, use the managed path, or the raw path gets encoded twice.
- **Bloom cost:**
  - UnrealBloomPass starts at half resolution with 5 mip levels and 11 HalfFloat render targets, about 13 full-screen draws per frame ([UnrealBloomPass.js](https://github.com/mrdoob/three.js/blob/r186/examples/jsm/postprocessing/UnrealBloomPass.js#L101-L105)).
  - Phone benchmarks: not found. Desktop forum reports describe it as heavy ([discourse.threejs.org/t/42606](https://discourse.threejs.org/t/42606) and [t/35476](https://discourse.threejs.org/t/35476), both old).
  - Utsubo says lower-resolution bloom is cheaper and post-processing at half resolution can roughly double frame rate ([utsubo.com/blog/threejs-best-practices-100-tips](https://utsubo.com/blog/threejs-best-practices-100-tips), 11 Sep 2026).
  - *Inference:* a cheaper option is an additive halo mesh that samples the same texture, with no extra passes.

**3. Editing UX in current tools**
- **xLights:**
  - Click to select, Ctrl-click to add, Shift box select, and a lasso in 3D. Also linked sets, Bulk Edit Rotate X/Y/Z, and Align to the first selected model ([manual.xlights.org/.../moving-model-objects](https://manual.xlights.org/xlights/chapters/chapter-four-tabs/moving-model-objects), undated). The manual says there is "no Undo" for dragging and alignment.
  - The source code has Translate, Rotate, XYTranslate and Elevate handle tools with per-axis colored handles ([xLights src-core/models/ModelScreenLocation.cpp](https://github.com/xLightsSequencer/xLights/blob/fbfaf0c6caf61c2c0d55e195334d17b4c399a98a/src-core/models/ModelScreenLocation.cpp), GitHub).
  - `.xmodel` import keeps relative positions and rescales to the layout's ruler ([manual.xlights.org/.../download-import-models](https://manual.xlights.org/xlights/chapters/chapter-four-tabs/download-import-models)).
  - Snapping: not found.
- **Chromatik:** an inspector with X/Y/Z and Yaw/Pitch/Roll, a Move Fixtures mouse mode (⇧⌘F), duplicate (⌘D), and tags for grouping. Fixtures are nested JSON `.lxf` files, and models import/export as `.lxm` ([chromatik.co/guide/model-definition](https://chromatik.co/guide/model-definition), ©2026). A 3D gizmo: not found.
- **grandMA3 2.3:**
  - Numeric position in meters and rotation in degrees.
  - Step sizes of 10 cm/1°, 1 cm/0.1° or 1 mm/0.01°, a choice of stage or object axes, and single or group rotation.
  - An Arrangement tool for Line, Grid and Circle (radius, start angle, angle range, rotate to center), with a purple preview before Apply ([help.malighting.com/grandMA3/2.3/HTML/patch_position_fixtures.html](https://help.malighting.com/grandMA3/2.3/HTML/patch_position_fixtures.html)).
- **Capture:** circular arrays come from Clone with the rotation anchor at the circle's center and an angle of 360/N (capture.se forum threads [8539](https://www.capture.se/Support/Forum/aft/8539) and [239](https://www.capture.se/Support/Forum/aft/239), old).
- **QLC+ v5:** numeric position in mm and rotation in degrees, edits applied relative to a group selection, "Pick a 3D point" to aim fixtures, and mesh import (.obj/.dae/.3ds/.stl/.blend) ([docs.qlcplus.org/v5/fixtures-and-functions/3d-view](https://docs.qlcplus.org/v5/fixtures-and-functions/3d-view)).
- **three.js editor:** translate, rotate and scale buttons only (no snap toggle in [Toolbar.js](https://github.com/mrdoob/three.js/blob/r186/editor/js/Toolbar.js)), Undo/Redo, Clone, Center, Delete, and JSON project files. It exports GLB, GLTF, OBJ, PLY, STL, USDZ and DRC ([editor/js](https://github.com/mrdoob/three.js/tree/r186/editor/js) at r186).
- **Pixelblaze:** a map is either an explicit [x,y,z] array or a JS function of the pixel count (newscrewdriver.com, [2019](https://newscrewdriver.com/2019/07/04/pixelblaze-pixel-map-for-led-helix/) and [2022](https://newscrewdriver.com/2022/08/04/orthogonal-fans-with-pixelblaze-3d-mapping/), old). Official docs: not found.
- **Exchange format:** MVR 1.6 (DIN SPEC 15801, recognized 13 Nov 2023, old) is the standard for passing rigs between consoles, CAD and previz tools ([github.com/mvrdevelopment/spec](https://github.com/mvrdevelopment/spec)).
- Not found: MadMapper 3D placement tools, Depence, Vectorworks Vision, and camera presets in these tools.
- *Inference, the small set that covers most needs:*
  - Selection plus a TransformControls gizmo with `translationSnap`/`rotationSnap` and world/local space.
  - A numeric inspector for position plus yaw/pitch/roll.
  - Duplicate, and a line and circle/arc array tool with a preview, like grandMA3's.
  - Multi-select, undo/redo, top/front/side/perspective camera presets, and JSON import/export.
  - Measuring can wait.

**4. Touch and phone constraints**
- **OrbitControls:** one finger rotates, two fingers dolly and pan. It sets `touchAction='none'`, damping is off by default, and `zoomToCursor` is optional ([examples/jsm/controls/OrbitControls.js](https://github.com/mrdoob/three.js/blob/r186/examples/jsm/controls/OrbitControls.js#L508) at r186; damping [L209](https://github.com/mrdoob/three.js/blob/r186/examples/jsm/controls/OrbitControls.js#L209), `zoomToCursor` [L306](https://github.com/mrdoob/three.js/blob/r186/examples/jsm/controls/OrbitControls.js#L306)).
- **TransformControls:**
  - Hover only fires for mouse and pen, but pointer-down runs hover then down, so a finger can grab an axis.
  - It has a `size` property and fires `dragging-changed` ([TransformControls.js](https://github.com/mrdoob/three.js/blob/r186/examples/jsm/controls/TransformControls.js#L1020); `size` at [L924](https://github.com/mrdoob/three.js/blob/r186/examples/jsm/controls/TransformControls.js#L924), `dragging` at [L229-L236](https://github.com/mrdoob/three.js/blob/r186/examples/jsm/controls/TransformControls.js#L229-L236)). Use that event to turn OrbitControls off while dragging ([discourse.threejs.org/t/27572](https://discourse.threejs.org/t/27572), old).
  - Users found the three.js editor hard to use on a phone ([discourse.threejs.org/t/18362](https://discourse.threejs.org/t/18362), old).
- **Budgets:** cap the pixel ratio at 2. On mobile, aim for "<100 draw calls and <100,000 vertices" (Don McCurdy, quoted in [utsubo.com/blog/threejs-best-practices-100-tips](https://utsubo.com/blog/threejs-best-practices-100-tips), 11 Sep 2026). A lower-authority guide suggests a 1.5 cap on phones ([skills.sh/5dlabs/cto/three-js](https://skills.sh/5dlabs/cto/three-js), undated).
- *Inference:* an instanced design needs about 1 to 3 draw calls whatever the tube count. 300 low-poly cylinders come to roughly 25k vertices. The texture gives LED detail per pixel without adding vertices.

## Sources

- https://github.com/mrdoob/three.js/tags
- https://registry.npmjs.org/three/latest
- https://github.com/mrdoob/three.js/blob/r186/LICENSE
- https://threejs.org/manual/pages/installation.html
- https://github.com/mrdoob/three.js/wiki/Migration-Guide
- https://github.com/mrdoob/three.js/blob/r186/src/renderers/WebGLRenderer.js#L312
- https://github.com/mrdoob/three.js/blob/r186/src/renderers/WebGLRenderer.js#L277
- https://threejs.org/manual/pages/webgpurenderer.html
- https://utsubo.com/blog/threejs-2026-what-changed
- https://web.dev/blog/webgpu-supported-major-browsers
- https://caniuse.com/webgpu
- https://threejs.org/docs/pages/InstancedMesh.html
- https://discourse.threejs.org/t/11271
- https://discourse.threejs.org/t/72996
- https://github.com/mrdoob/three.js/blob/r186/src/textures/DataTexture.js#L32
- https://github.com/mrdoob/three.js/blob/r186/src/textures/DataTexture.js#L60
- https://github.com/mrdoob/three.js/blob/r186/src/textures/DataTexture.js#L71
- https://github.com/mrdoob/three.js/blob/r186/src/textures/DataTexture.js#L81
- https://threejs.org/manual/pages/color-management.html
- https://github.com/mrdoob/three.js/blob/r186/src/renderers/webgl/WebGLTextures.js#L2441-L2451
- https://github.com/mrdoob/three.js/blob/r186/examples/jsm/postprocessing/OutputPass.js#L97-L104
- https://github.com/mrdoob/three.js/blob/r186/examples/jsm/postprocessing/UnrealBloomPass.js#L101-L105
- https://discourse.threejs.org/t/42606
- https://discourse.threejs.org/t/35476
- https://utsubo.com/blog/threejs-best-practices-100-tips
- https://manual.xlights.org/xlights/chapters/chapter-four-tabs/moving-model-objects
- https://github.com/xLightsSequencer/xLights/blob/fbfaf0c6caf61c2c0d55e195334d17b4c399a98a/src-core/models/ModelScreenLocation.cpp
- https://manual.xlights.org/xlights/chapters/chapter-four-tabs/download-import-models
- https://chromatik.co/guide/model-definition
- https://help.malighting.com/grandMA3/2.3/HTML/patch_position_fixtures.html
- https://www.capture.se/Support/Forum/aft/8539
- https://www.capture.se/Support/Forum/aft/239
- https://docs.qlcplus.org/v5/fixtures-and-functions/3d-view
- https://github.com/mrdoob/three.js/blob/r186/editor/js/Toolbar.js
- https://github.com/mrdoob/three.js/tree/r186/editor/js
- https://newscrewdriver.com/2019/07/04/pixelblaze-pixel-map-for-led-helix/
- https://newscrewdriver.com/2022/08/04/orthogonal-fans-with-pixelblaze-3d-mapping/
- https://github.com/mvrdevelopment/spec
- https://github.com/mrdoob/three.js/blob/r186/examples/jsm/controls/OrbitControls.js#L508
- https://github.com/mrdoob/three.js/blob/r186/examples/jsm/controls/OrbitControls.js#L209
- https://github.com/mrdoob/three.js/blob/r186/examples/jsm/controls/OrbitControls.js#L306
- https://github.com/mrdoob/three.js/blob/r186/examples/jsm/controls/TransformControls.js#L1020
- https://github.com/mrdoob/three.js/blob/r186/examples/jsm/controls/TransformControls.js#L924
- https://github.com/mrdoob/three.js/blob/r186/examples/jsm/controls/TransformControls.js#L229-L236
- https://discourse.threejs.org/t/27572
- https://discourse.threejs.org/t/18362
- https://skills.sh/5dlabs/cto/three-js
