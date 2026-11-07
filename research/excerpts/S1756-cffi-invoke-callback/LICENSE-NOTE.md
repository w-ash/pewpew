# Excerpt provenance — S1756 cffi takes the GIL to run a callback

- project: cffi
- license: MIT (upstream LICENSE)
- pinned: python-cffi/cffi@e20c65d938842f82ce63983150b286956081cb27
- paths / contents:
  - `src/c/_cffi_backend.c` lines 6278–6290 (fetched at the pin on 2026-11-06): `invoke_callback`
    (L6280–6285) calls `gil_ensure()` before `general_invoke_callback`.
- why excerpted: ADR-009's 2026-11-06 amendment "live input": PortAudio's real-time thread would wait
  for the GIL while the render loop holds it.

Licence text: `../LICENSES/MIT.txt`. The upstream `LICENSE` carries no
copyright line; it refers to "the authors", whom upstream `AUTHORS` names
(Armin Rigo, with help from Maciej Fijałkowski).
