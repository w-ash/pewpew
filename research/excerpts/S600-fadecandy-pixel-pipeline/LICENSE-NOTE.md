# License note — Fadecandy firmware excerpts

- project: Fadecandy (firmware for Teensy 3.x LED controller)
- source repo: https://github.com/PimentNoir/fadecandy (community mirror;
  original scanlime/fadecandy deleted by the author [S015][S027])
- pinned: PimentNoir/fadecandy@36f616158f195a327f8486474af2956dad52881d
- license: MIT
- copyright: Copyright (c) 2013 Micah Elizabeth Scott
- excerpted: 2026-07-03, source entry [S600]

Files here are verbatim single-function excerpts (with an added provenance
header comment), preserved because the upstream repo is a mirror of a deleted
original:

| file | upstream path | lines | why |
|---|---|---|---|
| fc_pixel.cpp | firmware/fc_pixel.cpp | 25-89 | the per-pixel pipeline: keyframe interpolation (x257 trick), LUT call, temporal-dither residual carry, round/clamp to 8-bit |
| fc_pixel_lut.cpp | firmware/fc_pixel_lut.cpp | 26-86 | 257-entry 16-bit LUT with linear interpolation (SMUADX form + readable reference form in comment) |
| fadecandy.cpp | firmware/fadecandy.cpp | 97-120 | keyframe interpolation coefficient from millis() timestamps, 16-bit fixed point |

MIT license text (from the repo's per-file headers and top-level LICENSE):

The MIT License (MIT)

Copyright (c) 2013 Micah Elizabeth Scott

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
