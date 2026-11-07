"""Pure, vectorized, deterministic NumPy primitives for effect ops.

- `vec`: the shared convention, points as per-axis float32 arrays.
- `noise`: value and gradient noise, fBm, ridged, turbulence, curl, warp.
- `space`: coordinate ops: rotate, scale, polar, kaleidoscope, mirror,
  twist, tunnel, repeat.
- `sdf`: signed distance functions and smooth operators.
- `sample`: linear field reads, advection, texture projections.
- `grid`: deposit of points into a field.
- `knn`: nearest-neighbour graphs and diffusion, wave and Gray-Scott steps.

Each function takes and returns float32 arrays, reads no clock and no global
RNG, and gives the same bytes for the same inputs. Import the modules
directly, for example `from pewpew.fx.prims import noise`.
"""
