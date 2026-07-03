# Code reading: marimapper

- repo: https://github.com/TheMariday/marimapper
- pinned: TheMariday/marimapper@7dc5f799a1b7c180573c2632f6d12a3be0cbf4fa (v3.4.2, last commit 2026-03-29)
- license: GPL-3.0 (LICENSE is verbatim GPLv3) [S670:LICENSE#L1-L5]
- accessed: 2026-07-03
- source: [S670]

Camera-based 3D LED mapper: blinks LEDs one at a time from a webcam-facing
scan, detects the lit blob with OpenCV, and — this is the signature trick —
feeds LED IDs as pre-matched "keypoints" into COLMAP's incremental SfM
pipeline, sidestepping feature detection/matching entirely. Multiple
hand-held camera views around the object yield a full 3D map with normals.

## How it achieves its signature quality

### Process architecture & data flow

Four `multiprocessing.Process` workers wired by queues, started by `Scanner`
[S670:marimapper/scanner.py#L48-L115]:

```
DetectorProcess --(LED2D via Queue2D)--> SFM process --(list[LED3D] via Queue3D)--> VisualiseProcess
        |                                   |
        +--> FileWriterProcess (2D csv)     +--> FileWriterProcess (led_map_3d.csv)
        <--(Queue3DInfo: per-LED status)----+   (SFM feeds reconstruction status back to
                                                 the detector, which paints it onto the
                                                 actual LEDs via backend.set_leds)
```

- The SFM process re-runs a **full reconstruction from scratch after every new
  detection** (`update_sfm` on each `DETECT` message), then rescales,
  gap-fills, recenters, adds normals, and pushes to the visualizer — live
  feedback while you scan [S670:marimapper/sfm_process.py#L101-L211].
- Interactive loop: user is prompted "Start scan? [y/n]" per view; each scan
  sweeps the LED index range once; `view_id` increments per accepted scan
  [S670:marimapper/scanner.py#L176-L199].
- Start method is forced to `spawn` to dodge an Open3D
  `estimate_normals` fork crash on Linux [S670:marimapper/scanner.py#L17-L25,
  L65].

### Detection method: strictly per-LED blink, O(n) per view

- **One LED at a time.** `detect_leds` iterates `led_id` over the range and
  calls `enable_and_find_led` per LED [S670:marimapper/detector_process.py#L49-L78].
- `enable_and_find_led` [S670:marimapper/detector.py#L137-L186]:
  1. wait until **no** LED is visible (3 s darkness timeout, else abort with
     a warning — "an led is already visible");
  2. `backend.set_led(id, True)`, poll frames until a blob is found or an
     adaptive timeout expires;
  3. `set_led(id, False)`, wait for darkness again (re-sending `off` and
     retrying if the LED stays lit).
- **Adaptive latency timeout**: `TimeoutController` keeps the last 20
  on→detected response times and sets timeout = 90th percentile x 1.5 (default
  1.0 s until 10 samples exist) [S670:marimapper/timeout_controller.py#L4-L31].
  This is how it copes with slow backends (WLED HTTP, Pixelblaze websocket)
  without a fixed worst-case delay.
- **Binary coding exists but is disabled.** `detector_fast.py` implements
  binary-coded frames (each frame lights every LED whose ID has bit k set,
  O(log n) captures) but the file's own docstring says it is deliberately
  unused: "it kind of works... It works in ideal scenarios but little else
  beside... Keep it simple, keep it reliable"
  [S670:marimapper/detector_fast.py#L1-L8]. Nothing imports it.
- **Movement check**: after a view completes, LED[first] is re-lit and
  re-detected; if its 2D position moved > 0.01 in normalized units (1% of
  image width), the whole view is discarded (`DELETE`)
  [S670:marimapper/detector_process.py#L183-L217].
- **Sanity precondition**: before each scan the backend is blackened and one
  frame is checked; if anything is already visible the scan FAILs
  [S670:marimapper/detector_process.py#L151-L166].

Supported backends (registry): dummy, custom (user .py file), fadecandy
(OPC), fcmega (serial), pixelblaze, wled (HTTP JSON API), artnet (raw UDP)
[S670:marimapper/backends/backend_utils.py#L9-L27].

### Camera stack

- Plain `cv2.VideoCapture`, trying `CAP_DSHOW`, then `CAP_V4L2`, then
  `CAP_ANY` [S670:marimapper/camera.py#L29-L38].
- Camera control is entirely via `cv2.CAP_PROP_*`: on scan start it snapshots
  default settings, then sets autofocus off, manual exposure mode, gain 0,
  and a dark exposure (default `-10`; failures are logged and tolerated with
  advice to darken the room and tune `--threshold`)
  [S670:marimapper/detector.py#L99-L120][S670:marimapper/camera.py#L60-L92].
- `Camera.eat(count=30)` reads and discards 30 frames after any settings
  change so buffered/stale frames don't leak into detection
  [S670:marimapper/camera.py#L94-L96].
- No resolution/fps configuration, no camera calibration, no fisheye support
  (distortion is left to COLMAP's radial model, below).

### Blob detection precision (sub-pixel, per stage)

`find_led_in_image` [S670:marimapper/detector.py#L25-L57]:

1. grayscale convert (BGR→GRAY);
2. `cv2.threshold(..., THRESH_TOZERO)` at threshold 128 (default) — keeps
   graylevels above threshold rather than binarizing, so brightness
   information survives;
3. `cv2.findContours`; if several blobs, pick the contour with the largest
   **sum of masked pixel intensities** (`contour_brightness`,
   drawContours-mask + `cv2.sumElems`) — brightest region wins, not largest
   [S670:marimapper/detector.py#L17-L22, L37-L39];
4. centroid = intensity moments of the contour (`m10/m00`, `m01/m00`) —
   **sub-pixel** center via image moments;
5. normalize: `u = cx/width`; `v = (cy + (width-height)/2)/width` — both
   coordinates are divided by image **width**, with v letter-boxed so the
   coordinate frame is a square of side `width` centered on the image. This
   makes 2D CSVs resolution-independent and aspect-ratio-independent.

Precision notes: centroid is float sub-pixel, but there is no Gaussian
fitting or refinement; accuracy is whatever the moments of a
possibly-bloomed blob give. A defensive `center==0 → None` check papers over
an unexplained degenerate case (comment: "Am I going to find out why, no")
[S670:marimapper/detector.py#L46-L49].

### 3D reconstruction: COLMAP incremental SfM with pre-matched features

This is the load-bearing idea. Instead of detecting/matching visual
features, marimapper writes a **synthetic COLMAP database** where the LED ID
is the correspondence:

- `populate_database` creates one dummy "image" per view; keypoint index i
  in every image is LED i's detection, scaled into a fictitious
  2000x2000-px camera (`ARBITRARY_SCALE`), with `(1-u, 1-v)` flipped so the
  model comes out y-up [S670:marimapper/database_populator.py#L58-L108].
- For every pair of views, `add_two_view_geometry` is given the identity
  matches `[i, i]` for all LED IDs seen in both views — perfect,
  outlier-free correspondences [S670:marimapper/database_populator.py#L110-L124].
- Camera intrinsics are a guess: principal point at center, focal from an
  assumed FOV (default 60 deg, `f = (w/2)/tan(fov/2)`); model selectable
  among pinhole / radial (default, one k coefficient) / opencv /
  opencv_full, all distortion params initialized to 0 and refined by
  COLMAP's bundle adjustment [S670:marimapper/database_populator.py#L25-L48, L86-L93].
- `pycolmap.incremental_mapping` (pinned `pycolmap==3.11.1`; ">3.12 breaks
  2-view tracks" [S670:pyproject.toml#L12]) runs with loosened thresholds
  because LED "features" are sparse: `ignore_two_view_tracks=False`,
  `min_num_matches=9` (default 15), `abs_pose_min_num_inliers=9` (default
  30), `init_min_num_inliers=50` (default 100) [S670:marimapper/sfm.py#L40-L44].
- If COLMAP produces multiple disconnected sub-maps, only the **largest** is
  kept; the author notes merging them is unsound without a relative
  transform [S670:marimapper/sfm.py#L54-L74].
- Reading back `points3D.bin`: each 3D point's LED ID is recovered as
  `point2D_idxs[0]` (keypoint index == LED ID); camera poses are inverted
  (`R^T`, `-R^T t`) to get view positions; duplicate LED IDs are merged by
  averaging positions/normals and summing reprojection error
  [S670:marimapper/model.py#L13-L43][S670:marimapper/led.py#L284-L319].

Post-processing, in order [S670:marimapper/sfm_process.py#L135-L157]:

1. **rescale**: scale the whole map so the **median distance between
   consecutive LED IDs is 1.0** [S670:marimapper/led.py#L191-L213];
2. **fill_gaps**: linearly interpolate runs of up to `max_missing` (default
   5) undetected LEDs between neighbours, but only if the implied
   per-LED spacing is within ±20% of 1.0 (so it won't interpolate across a
   physical fold) [S670:marimapper/led.py#L228-L281];
3. **recenter**: subtract the median position [S670:marimapper/led.py#L216-L225];
4. **add_normals**: Open3D `estimate_normals` on the point cloud, sign-fixed
   to face the mean position of the cameras that saw each LED
   [S670:marimapper/sfm_process.py#L26-L50].

Accuracy: there is no metric ground truth — scale is normalized to LED
pitch, reprojection error per LED is carried through to the CSV as `error`
(in COLMAP's fictitious-2000px pixel units). Degenerate cases handled in
code: 0 LEDs or ≤1 view → empty result [S670:marimapper/sfm.py#L23-L33]; low
inter-view overlap gets a printed warning (<10 shared LEDs or <50% overlap
means the new view may be dropped by SfM) [S670:marimapper/sfm_process.py#L188-L209].
Classic SfM degeneracies (pure camera rotation, all-collinear LED strips,
two views with a tiny baseline) are *not* explicitly handled — they just
yield "0 LEDs reconstructed" and the user is told to add more views.

### Map output format

Written by the file-writer process [S670:marimapper/file_writer_process.py#L34-L63]:

- Per view: `led_map_2d_<YYYYmmdd-HHMMSS>.csv` with header `index,u,v`,
  normalized image coordinates as above [S670:marimapper/file_tools.py#L57-L65].
  These files are also the **resume state**: on startup every `*.csv` in the
  output dir with that header is reloaded as an existing view
  [S670:marimapper/file_tools.py#L41-L54].
- 3D: single `led_map_3d.csv`, header `index,x,y,z,xn,yn,zn,error`
  [S670:marimapper/file_tools.py#L68-L85]. Units: **1.0 = median spacing
  between consecutive LEDs**; origin = median LED position; y+ up
  (approximately — orientation is otherwise arbitrary/gauge-free from SfM).
  `index` is the LED index and rows are sorted, but **missing LEDs are
  simply absent** (sparse), and interpolated/merged LEDs are not flagged in
  the file.
- A Pixelblaze uploader converts the CSV to a normalized pixel map
  [S670:marimapper/backends/pixelblaze/upload_map_to_pixelblaze.py].

**Pewpew consumption**: trivially — it's a 5-minute CSV parser. The only
decisions pewpew must make: rescale from LED-pitch units to meters (needs
one real-world measurement, e.g. actual LED spacing), choose axis
conventions, and decide how to handle absent indices.

### Backend extension API — adding a pewpew/DDP backend

The duck-typed backend contract is exactly two methods, plus one optional:

- `get_led_count() -> int`
- `set_led(led_index: int, on: bool)` — enforced arity checks in
  `check_backend` [S670:marimapper/backends/custom/custom_backend.py#L39-L57]
- optional `set_leds(buffer: list[[r,g,b]])` — used only to blacken the rig
  and to paint reconstruction-status colors between scans; absence is caught
  via `AttributeError` and tolerated [S670:marimapper/detector_process.py#L24-L47].

Two integration routes:

1. **Zero-fork route (recommended for GPL hygiene)**: `marimapper --backend
   custom my_backend.py` dynamically loads any user Python file exposing a
   `Backend` class [S670:marimapper/backends/custom/custom_backend.py#L19-L36].
   A pewpew DDP backend is ~30 lines: hold a socket, `set_led` sends a DDP
   frame with one white pixel. The WLED backend (75 lines total, HTTP) is
   the template [S670:marimapper/backends/wled/wled_backend.py#L15-L75].
2. In-tree route: add a module under `marimapper/backends/<name>/` with a
   `<name>_backend_factory(args)` + `<name>_backend_set_args(parser)` pair
   and register both in the two dicts in `backend_utils.py`
   [S670:marimapper/backends/backend_utils.py#L9-L27]. Only worth it as an
   upstream PR.

Note the timing model: `set_led` is synchronous and the detector's adaptive
timeout absorbs transport latency, so even a slow control path works; a DDP
backend would be near-instant and drive the timeout down to ~the camera
frame time.

## Detection failure modes (from issues + code)

From the tracker (accessed 2026-07-03) [S671]:

- **Reflections / secondary blobs** (#66, #54): reflections off glass/shiny
  surfaces can have higher *peak* brightness than the diffused LED,
  especially with wide-angle lenses and vignetting; "Reflections really
  confuse the SfM". The fix now in code — pick the contour with the highest
  *integrated* brightness [S670:marimapper/detector.py#L17-L22, L37-L39] —
  came directly from #66; before it users needed exposure at -8 EV or lower
  to suppress reflections (#54) [S671].
- **Detector hangs when nothing is detected** (#84, open): with a
  too-high default threshold for the setup, the per-LED loop stalls in the
  post-detection darkness wait and the scan never progresses; reported as a
  frustrating first-run experience [S671].
- **No working exposure control on macOS** (#51): `CAP_PROP_EXPOSURE` fails
  on Macs even for supported webcams; users resort to third-party apps
  (Camo Studio, "Webcam Settings") to force exposure down. #64 (open) asks
  for automatic exposure/threshold calibration [S671]. The code anticipates
  the failure with a warning and `--threshold` fallback
  [S670:marimapper/detector.py#L110-L115].
- **Large multi-section scans corrupt** (#48): a ~5000-LED Pixelblaze rig
  scanned in 200-300 LED sections saw LEDs disappearing and previously-good
  maps becoming unusable across sessions [S671].
- **Reconstructed LED count can *decrease* after adding a view** (#37):
  a new view can perturb bundle adjustment enough that previously-placed
  LEDs fall below inlier thresholds; no user-tunable confidence knob [S671].
- **Disconnected sub-maps** (#81, open): sections with insufficient overlap
  reconstruct as separate COLMAP maps; only the largest is kept
  [S670:marimapper/sfm.py#L54-L74].
- **"An led is already visible" aborts**: any stray light (status LED,
  monitor glow, LED that failed to turn off, e.g. a stuck WLED segment)
  trips the darkness precondition [S670:marimapper/detector.py#L149-L157].
- **Movement check false positives** on hand-held scans; hence the
  `--disable_movement_check` flag wired through the CLI
  [S670:marimapper/scripts/scanner_cli.py#L58].
- **Dense strips / occlusion**: LEDs facing away from the camera are simply
  missed in that view; reconstruction needs each LED in ≥2 views, hence the
  UNRECONSTRUCTABLE status class [S670:marimapper/led.py#L112-L129] and the
  gap-fill interpolator as the fallback.
- **pycolmap version fragility**: 2-view track support broke for
  pycolmap > 3.12, hence the `==3.11.1` pin [S670:pyproject.toml#L12].
- Open3D `estimate_normals` crashes under fork start method on Linux
  (marimapper issue #46), forcing `spawn` [S670:marimapper/scanner.py#L17-L25].

## GPLv3 boundary analysis

- License is plain GPLv3 (not AGPL, not LGPL) [S670:LICENSE#L1-L5].
- GPLv3 obligations attach to **distribution of the program or derivative
  works**, not to use, and not to programs that merely execute it as a
  separate process communicating "at arm's length" (files, pipes, CLI args)
  — the FSF's own GPL FAQ treats exec-with-file-exchange as two separate
  programs so long as they are not sharing address space/linking [S672].
- Marimapper is *designed* for exactly this boundary: it is a standalone
  `pipx install marimapper` CLI whose entire output is CSV files in a
  directory [S670:pyproject.toml#L53-L57][S670:marimapper/file_tools.py#L57-L85].
  **Pewpew can shell out to `marimapper` (or just consume a user-produced
  `led_map_3d.csv`) and stay unconstrained.** Even bundling the unmodified
  marimapper wheel alongside pewpew is fine as "mere aggregation" provided
  pewpew doesn't import marimapper as a library.
- What pewpew must NOT do without going GPL: `import marimapper`, vendor
  its code, or port nontrivial code verbatim. Writing a custom-backend .py
  file *for marimapper* (route 1 above) arguably becomes a marimapper
  plugin; safest is to ship that ~30-line backend file under GPLv3 itself
  (it's trivial and contains no pewpew internals) or upstream it.
- Reimplementing the *ideas* (blink-and-blob, synthetic COLMAP DB) from this
  document is copyright-safe; pycolmap itself is BSD-3 (COLMAP license), so
  a clean-room pewpew mapper using pycolmap directly has no GPL exposure.

## What pewpew should steal

1. **The synthetic-COLMAP-database trick** — LED index as keypoint index,
   identity matches between all view pairs, guessed intrinsics refined by
   bundle adjustment, loosened inlier thresholds for sparse features
   [S670:marimapper/database_populator.py#L58-L124][S670:marimapper/sfm.py#L40-L52].
   This turns a hard correspondence problem into zero work and reuses a
   world-class BA engine (pycolmap, BSD).
2. **Normalized square image coordinates** (divide u and v by width,
   letterbox v) — makes per-view 2D captures camera/resolution independent
   [S670:marimapper/detector.py#L51-L57].
3. **Adaptive per-backend latency timeout** (P90 x 1.5 of observed on→seen
   times) instead of fixed sleeps [S670:marimapper/timeout_controller.py].
4. **Darkness preconditions + LED-off confirmation + movement re-check**
   as scan validity gates [S670:marimapper/detector.py#L137-L186]
   [S670:marimapper/detector_process.py#L183-L217].
5. **LED-pitch normalization + median-centering + physically-gated linear
   gap interpolation (±20% spacing)** [S670:marimapper/led.py#L191-L281].
6. **Camera-facing normal estimation** (Open3D normals, sign-disambiguated
   toward observing cameras) — directly useful for pewpew effects that need
   surface orientation [S670:marimapper/sfm_process.py#L26-L50].
7. **Status feedback rendered onto the LEDs themselves** (green =
   reconstructed, red = unreconstructable...) — great UX with zero extra UI
   [S670:marimapper/detector_process.py#L33-L47].
8. **Frame-buffer flush after camera setting changes** (`eat(30)`)
   [S670:marimapper/camera.py#L94-L96].

## What to avoid

- **Binary/Gray-code detection as the default**: the author tried it and
  shelved it as unreliable outside ideal conditions
  [S670:marimapper/detector_fast.py#L1-L8]. If pewpew wants O(log n)
  capture, it needs to solve blob *identity association* across frames and
  bloom/occlusion robustness that marimapper punted on.
- **Full SfM re-run per detection**: O(views x LEDs) re-reconstruction after
  every single LED gets slow on big rigs; fine for live feedback, wrong as
  an architecture [S670:marimapper/sfm_process.py#L111-L143].
- **Linear scan over `list[LED]` everywhere** (`get_led`, `get_next` are
  O(n) inside O(n) loops) [S670:marimapper/led.py#L137-L166] — use dicts.
- The **fragile process choreography**: comments like "DO NOT MOVE THIS /
  FATAL WEIRD CRASH IF THIS ISN'T IMPORTED FIRST DON'T ASK"
  [S670:marimapper/scanner.py#L1-L2] and the forced global `spawn` start
  method show multiprocessing + Open3D + OpenCV GUI in one app is a tarpit.
- **Unpinned camera geometry assumptions**: guessed 60 deg FOV with radial
  model works because BA refines it, but wide-angle/fisheye cameras will
  need `camera_model_opencv_full` and possibly fail; no calibration path.
- The sparse CSV with silent gaps and unflagged interpolated points — pewpew's
  format should mark provenance (measured vs interpolated) per LED.

## Open questions

- Real-world accuracy is unquantified anywhere in the repo (no benchmark of
  reconstruction error vs ground truth); only per-point COLMAP reprojection
  `error` is exported. Unknown how it degrades with cheap wide-FOV webcams.
- Why detected centroids occasionally come back at exactly 0 (the guarded
  degenerate case in `find_led_in_image`) is unexplained even by the author
  [S670:marimapper/detector.py#L46-L49].
- Whether COLMAP's multi-submap output (disconnected components) could be
  merged with extra views is explicitly left unresolved upstream
  [S670:marimapper/sfm.py#L54-L59].
- `led_map_2d_*.csv` resume assumes alphabetical filename order equals view
  order and that all CSVs in the dir belong to this rig — collision behavior
  with foreign CSVs is untested (author's own comment questions the code)
  [S670:marimapper/file_tools.py#L41-L54].
