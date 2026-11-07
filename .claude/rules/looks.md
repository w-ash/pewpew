---
paths:
  - "examples/**"
  - "src/pewpew/compose/**"
---

# Looks and the layer stack

- A look file is a looks file of version 4, and every knob goes by its address
  (`layers.<layer>.<node>.<arg>`). Ids never change once a look ships.
- Before committing a look under `examples/`, run
  `uv run python -m pewpew verify looks examples/` and keep it green:
  it checks, no layer raises, at most 3 flashes a second, not all black,
  and every knob changes the picture. Look at its sheet too
  (`fx render FILE --out sheet.png`): the gate passes looks that read badly.
- Write looks with the `authoring-looks` skill's loop: catalog first,
  never op args from memory.
- In `src/pewpew/compose/`, each layer's seed comes from the look's seed
  and the CRC-32 of the layer id (`layer_seed`), never `hash()`. Never
  regenerate the goldens (`tests/goldens/*.npz`) to make a compose change
  pass.
