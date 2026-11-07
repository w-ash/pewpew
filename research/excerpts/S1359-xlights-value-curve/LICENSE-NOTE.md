# LICENSE NOTE

- project: xLights (https://github.com/xLightsSequencer/xLights)
- license: GPL-3.0
- copyright: xLights contributors
- pinned: xLightsSequencer/xLights@a57c5ace577ca84421273d2f859a1a0c3f728297
- path: src-core/render/ValueCurve.cpp (L1555-L1607)
- excerpted: 2026-11-04, source entry [S1359]
- why excerpted: ADR-006's 2026-11-04 amendment cites these lines as the
  cost of storing values normalized: every load still carries a converter
  from 0-100 curves to real values, with a version check and a "cannot be
  converted automatically" warning.
- reuse caution: GPL-3.0. Reference only; never copy into pewpew.

Licence text: `../LICENSES/GPL-3.0.txt`.
