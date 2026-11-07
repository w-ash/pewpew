# Verbatim copy of the 2026-10-22 prototype (docs/studio/README.md), kept as found.
# ruff: noqa: E501, SIM115
"""Write an SVG of the two tube rings, tilted, in top and side view."""
import math

PHI = (1 + 5 ** 0.5) / 2
L, D = 100, 3                # tube length and diameter
N = 24
TILT = math.radians(30)      # inner end down, outer end up, about the tube midpoint
R_INNER = L / PHI
R_OUTER = R_INNER + L - L / PHI
MARGIN = 12
LABEL = 16                   # space above the side view for its label

HALF_RHO = L / 2 * math.cos(TILT)
HALF_Z = L / 2 * math.sin(TILT)
EXTENT = R_OUTER + L / 2 + HALF_RHO + D
W = 2 * (EXTENT + MARGIN)
TOP_C = W / 2
SIDE_H = LABEL + 2 * (HALF_Z + D + MARGIN)
SIDE_Z0 = W + LABEL + HALF_Z + D + MARGIN   # SVG y of z = 0 in the side view
H = W + SIDE_H


def tubes():
    """Return each tube as its inner and outer end points (x, y, z)."""
    out = []
    for r_start, offset in ((R_INNER, 0), (R_OUTER, 180 / N)):
        r_mid = r_start + L / 2
        for i in range(N):
            t = math.radians(offset + i * 360 / N)
            ends = []
            for rho, z in ((r_mid - HALF_RHO, -HALF_Z), (r_mid + HALF_RHO, HALF_Z)):
                ends.append((rho * math.cos(t), rho * math.sin(t), z))
            out.append(ends)
    return out


def line(x1, y1, x2, y2, color):
    return (f'    <line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
            f'stroke="{color}"/>')


def gray(t):
    v = round(0x11 + t * (0xBB - 0x11))
    return f"#{v:02X}{v:02X}{v:02X}"


all_tubes = tubes()
top = [line(TOP_C + a[0], TOP_C - a[1], TOP_C + b[0], TOP_C - b[1], "#111111")
       for a, b in all_tubes]

# The side view looks along +y: larger y is farther away, drawn first and lighter.
depth = lambda tube: (tube[0][1] + tube[1][1]) / 2
far = max(depth(t) for t in all_tubes)
side = [line(TOP_C + a[0], SIDE_Z0 - a[2], TOP_C + b[0], SIDE_Z0 - b[2],
             gray((depth((a, b)) + far) / (2 * far)))
        for a, b in sorted(all_tubes, key=depth, reverse=True)]

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W:.3f}" height="{H:.3f}" viewBox="0 0 {W:.3f} {H:.3f}">
  <rect width="100%" height="100%" fill="#FFFFFF"/>
  <g font-family="Helvetica, Arial, sans-serif" font-size="9" fill="#888888">
    <text x="6" y="14">Top</text>
    <text x="6" y="{W + 14:.3f}">Side</text>
  </g>
  <line x1="0" y1="{W:.3f}" x2="{W:.3f}" y2="{W:.3f}" stroke="#DDDDDD" stroke-width="0.5"/>
  <line x1="{MARGIN}" y1="{SIDE_Z0:.3f}" x2="{W - MARGIN:.3f}" y2="{SIDE_Z0:.3f}" stroke="#CCCCCC" stroke-width="0.5" stroke-dasharray="3 3"/>
  <g id="top-view" stroke-width="{D}" stroke-linecap="butt">
{chr(10).join(top)}
  </g>
  <g id="side-view" stroke-width="{D}" stroke-linecap="butt">
{chr(10).join(side)}
  </g>
</svg>
'''
open("golden-tubes.svg", "w").write(svg)
print(f"inner ring rho {R_INNER + L/2 - HALF_RHO:.1f}-{R_INNER + L/2 + HALF_RHO:.1f}, "
      f"outer ring rho {R_OUTER + L/2 - HALF_RHO:.1f}-{R_OUTER + L/2 + HALF_RHO:.1f}, "
      f"z {-HALF_Z:.1f} to {HALF_Z:.1f}")
