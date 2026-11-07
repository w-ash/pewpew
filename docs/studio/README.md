# pewpew studio

The studio arranges LED fixtures in 3D, runs pewpew's real effects on them, models the rig's
power, wiring and controllers, and shares an arrangement by link. It is hosted on fly.io.

- [`plan.md`](plan.md): the plan the maintainer approved on 2026-10-22. It covers the decisions,
  the workstreams and the verification.
- [`domain-model.md`](domain-model.md): the rig domain model. It has three parts: the catalog,
  the arrangement, and the wiring and power. This is the design every workstream builds to.
- [`planning/`](planning/): the planning reports, verbatim, from 2026-10-22 (the A0 handoff
  that started the work is in the project's notes, not in this repo):
  - [A1](planning/2026-10-22-a1-flyio-hosting-and-share-links.md): fly.io hosting and share
    links;
  - [A2](planning/2026-10-22-a2-threejs-viewer-and-editor.md): the three.js viewer and editor;
  - [A3](planning/2026-10-22-a3-power-wiring-controllers.md): power, wiring and controller
    modeling;
  - [A4](planning/2026-10-22-a4-fixture-model-prior-art.md): prior art for fixture, placement
    and power models;
  - [A5](planning/2026-10-22-a5-stack-and-libraries.md): the stack and libraries as of October
    2026.

The fixture record for the 1M LED Pixel Bar (INV-001) and the 1.5M 360 LED Tube (INV-002) is
the maintainer's fixture notes, which are not public. The record IDs these docs cite (INV-, PRT-,
RES-, Q-) are from those notes.

[`prototype/`](prototype/) holds a copy of the three.js prototype the studio grew from, made
2026-10-22: the viewer `golden-tubes-3d.html` (an artifact body with no html/head/body wrapper),
its renders `overview.png`, `point.png` and `eye.png`, and the 2D generators `rings.py` and
`tubes.py` with their SVGs. The visual check compares against `prototype/overview.png`.

## Sources

- The maintainer's fixture notes (fixture record, not public)
- `docs/studio/prototype/golden-tubes-3d.html`, `overview.png`, `point.png`, `eye.png`, `rings.py`, `tubes.py`
