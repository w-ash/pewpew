# Verbatim copy of the 2026-10-22 prototype (docs/studio/README.md), kept as found.
# ruff: noqa: F401, E501, SIM115
"""Write an SVG of two interleaved rings of radial 100x3 bars."""
import math

PHI = (1 + 5 ** 0.5) / 2
L, W = 100, 3
N = 24
OVERLAP = L / PHI            # 61.80: shared radial span of the two rings
R_INNER = L / PHI            # 61.80: gap from the center to the inner ring
R_OUTER = R_INNER + L - OVERLAP
EXTENT = R_OUTER + L
MARGIN = 10
SIZE = 2 * (EXTENT + MARGIN)
C = SIZE / 2


def ring(name, r, offset):
    rects = []
    for i in range(N):
        a = offset + i * 360 / N
        rects.append(
            f'    <rect x="{C + r:.3f}" y="{C - W / 2:.3f}" width="{L}" height="{W}" '
            f'transform="rotate({a:.3f} {C:.3f} {C:.3f})"/>'
        )
    return f'  <g id="{name}">\n' + "\n".join(rects) + "\n  </g>"


svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE:.3f}" height="{SIZE:.3f}" viewBox="0 0 {SIZE:.3f} {SIZE:.3f}" fill="#111111">
  <rect width="100%" height="100%" fill="#FFFFFF"/>
{ring("inner-ring", R_INNER, 0)}
{ring("outer-ring", R_OUTER, 180 / N)}
</svg>
'''
open("golden-rings.svg", "w").write(svg)
print(f"inner {R_INNER:.2f}-{R_INNER + L:.2f}, outer {R_OUTER:.2f}-{EXTENT:.2f}, overlap {OVERLAP:.2f}, canvas {SIZE:.1f}")
