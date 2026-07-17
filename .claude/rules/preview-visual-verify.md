---
paths:
  - "preview/**"
---

# Measurable ≠ visible

Changes to visual surfaces are verified BOTH ways before committing:

- **Eyeball a screenshot** (headless Playwright; binaries are cached under
  `~/Library/Caches/ms-playwright`). Metrics have passed while the render
  was scrambled (the lattice color/position desync) or imperceptible (torus
  precession at 10³ cells — motion must read to a human, not just to a diff).
- **Statistics on the actual pixel/state data** — eyes have missed what
  stats caught (comet sparkle ratcheting to permanent white).

Two gotchas from the standing Playwright harness: scroll a card into view
before sampling (IntersectionObserver culling freezes off-screen canvases),
and exclude the brightest stochastic elements (embers, wandering tongues)
from any centroid-based assertion.
