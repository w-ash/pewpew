# Excerpt provenance — S715 projectMM mapping build

- project: projectMM (MoonModules v3)
- license: GPL-3.0 (see upstream LICENSE). Excerpt kept verbatim for research
  citation/archival only — GPL-3.0 code must NOT be copied into pewpew source
  unless pewpew adopts a GPL-compatible license.
- copyright: ewowi (Ewoud Wijma) / MoonModules contributors
- pinned: ewowi/projectMM@d5ee07ce3d6c590019cbbde670de8c532b2df511
- path: src/light/layers/Layer.h (lines 320–507)
- why excerpted: the load-bearing mapping algorithm of the Layouts→Layers→Drivers
  pipeline — `rebuildLUT()` (fold physical coords through the static modifier
  chain, measured identity fast path, OOM degradation to 1:1),
  `isNaturalOrder()` (measured-not-declared identity check), and
  `buildFoldedLUT()` (counting-sort CSR build with the tight
  maxDest == driverCount bound). Cited in
  research/code-reading/modern-engines.md §A.
