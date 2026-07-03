# LICENSE NOTE

- project: LedFx (https://github.com/LedFx/LedFx)
- license: GPL-3.0 (LICENSE.txt in repo root)
- copyright: LedFx developers (Austin Hodges et al., per AUTHORS.rst)
- pinned: LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792
- path: ledfx/effects/melbank.py (constants L26-L32; Melbank.__init__ fragments L100-L108, L264-L287, L374-L378; Melbank.__call__ L380-L403)
- why excerpted: the signature audio-normalization pipeline — custom log
  frequency warp ("matt_mel"), tunable peak-isolation exponent, slow-release
  AGC via blurred-max ExpFilter, and the transient-emphasizing
  "filtered melbank" (band-pass over time). This chain is why LedFx effects
  look consistent across quiet and loud material.
- reuse caution: GPL-3.0 — reference for reimplementation ideas only; do not
  copy into a non-GPL pewpew codebase verbatim.
