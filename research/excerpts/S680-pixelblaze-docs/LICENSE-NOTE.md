# Excerpt provenance — S680 Pixelblaze official docs (language + mapper reference)

- project: simap/pixelblaze (official Pixelblaze docs repo, v3 branch)
- license: NO LICENSE FILE in the repo (docs for closed-source firmware).
  These files are retained VERBATIM solely for citation permanence — so the
  line-anchored ADR evidence survives upstream deletion. Do NOT reuse,
  reproduce, or adapt this text in pewpew code or docs; treat as
  all-rights-reserved reference material.
- copyright: Ben Hencke (simap) / ElectroMage
- pinned: simap/pixelblaze@20d169f30f7912b2245c57ab9bd721436324bf04 (v3 branch) [S680]
- paths / contents (complete files, fetched at the pinned sha 2026-07-03):
  - `README.expressions.md` (255 lines) — carries the ranges cited by ADR-005
    (#L19-L70, beforeRender(delta)/render(index,x,y,z) contract), ADR-010 and
    requirements Q-5 (#L23, delta-time animation independent of frame rate),
    comparison-matrix (#L25, 16.16 fixed-point), architecture §3
    (#L19-L23, #L151-L163).
  - `README.mapper.md` (78 lines) — carries #L12-L36 (normalized 0–1 "world
    units", editor auto-scaling of physical coordinates), cited by ADR-005,
    ADR-007, architecture §5, comparison-matrix.
- why excerpted: canonical statement of the Pixelblaze pattern-authoring and
  mapping model — the design precedent for pewpew's time-parameterized,
  world-unit pattern contract. Note: same underlying document as seed source
  [S304] (electromage.com docs); this repo copy is the pinned, line-citable
  form.
