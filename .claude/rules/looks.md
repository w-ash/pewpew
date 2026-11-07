---
paths:
  - "examples/**"
  - "src/pewpew/compose/**"
---

# Looks and the layer stack

- A look file is a looks file of version 4; a pattern goes by name,
  never by file path, and every knob by its address
  (`layers.<layer>.<node>.<arg>`). Ids never change once a look ships.
- Before committing a look under `examples/`, run
  `uv run python -m pewpew verify looks examples/` and keep it green:
  it checks, no layer raises, at most 3 flashes a second, not all black,
  and every knob changes the picture. Look at its sheet too
  (`fx render FILE --out sheet.png`): the gate passes looks that read badly.
- Write looks with the `authoring-looks` skill's loop: catalog first,
  never op args from memory.
- In `src/pewpew/compose/`, a one-layer stack must render byte for byte
  what its pattern alone renders, and each layer's seed comes from the
  look's seed and the CRC-32 of the layer id (`layer_seed`), never
  `hash()`. The goldens (`tests/goldens/*.npz`) hold both; never
  regenerate them to make a compose change pass.
