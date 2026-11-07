# License note

- project: WLED (https://github.com/wled/WLED)
- license: EUPL v1.2 or later
- copyright: Copyright (c) 2016 Harm Aldick; (c) 2016-present Christian Schwinne and individual WLED contributors
- pinned: wled/WLED@14709dd3ea9fca9e5164509772f6c75185e3ab63 [S645]
- excerpted path: wled00/FX_fcn.cpp#L1330-L1367, #L1781
- excerpted: 2026-11-05
- why: ADR-006 and ADR-021 cite L1330-L1367 for WLED's transition, which runs the mode of a copied old segment beside the new one; ADR-001 and ADR-002 cite L1781 for its 8-bit pipeline, where gamma is applied to the 8-bit pixel after brightness.

Licence text: `../LICENSES/EUPL-1.2.txt`, with the upstream notice "Copyright
(c) 2016-present Christian Schwinne and individual WLED contributors"
(`LICENSE` line 1 at the pin).
