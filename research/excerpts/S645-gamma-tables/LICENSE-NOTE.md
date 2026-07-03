# License note

- project: WLED (https://github.com/wled/WLED)
- license: EUPL v1.2 or later
- copyright: (c) 2016-present Christian Schwinne and individual WLED contributors
- pinned: wled/WLED@14709dd3ea9fca9e5164509772f6c75185e3ab63 [S645]
- excerpted path: wled00/colors.cpp#L647-L683
- excerpted: 2026-07-03
- why: Runtime-recomputed 8-bit gamma + inverse-gamma LUTs (inverse table built with -0.5 bias and used to pre-invert opacity so opacity scaling composes with gamma, issue #5343).
