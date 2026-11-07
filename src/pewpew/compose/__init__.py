"""The layer stack (architecture §2 stage 2): a look's layers, each running
a program, blended bottom to top into one frame.

`stack` holds the values (`Look`, `Layer`, `Route`, `layer_seed`),
`controls` every knob of a stack by address (`LayerControls`, `Controls`)
and the knobs a look would have (`look_controls`), and `compositor` the
running stack (`Compositor`), a `pewpew.render.Live` source the
crossfader fades between.
"""

from __future__ import annotations

from pewpew.compose.compositor import Compositor, LayerError, LiveLayer
from pewpew.compose.controls import MIX, Controls, Knob, LayerControls, Section, layer_address, look_controls
from pewpew.compose.stack import DEFAULT_FADE, Layer, Look, Route, layer_seed, stack_problems

__all__ = [
    "DEFAULT_FADE", "MIX", "Compositor", "Controls", "Knob", "Layer", "LayerControls", "LayerError",
    "LiveLayer", "Look", "Route", "Section", "layer_address", "layer_seed", "look_controls", "stack_problems",
]
