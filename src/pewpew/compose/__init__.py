"""The layer stack (architecture §2 stage 2): a look's layers, each running
a program, blended bottom to top into one frame.

`stack` holds the values (`Look`, `Layer`, `Route`, `layer_seed`),
`controls` every knob of a stack by address (`LayerControls`, `Controls`),
and `compositor` the running stack (`Compositor`), a `pewpew.render.Live`
source the crossfader fades between, and the knobs a stack would have
(`controls_of`).
"""

from __future__ import annotations

from pewpew.compose.compositor import Compositor, LayerError, LiveLayer, Resolved, controls_of
from pewpew.compose.controls import MIX, Controls, Knob, LayerControls, Section, layer_address
from pewpew.compose.stack import (
    DEFAULT_FADE,
    PATTERN,
    Layer,
    Look,
    Route,
    layer_seed,
    pattern_layer,
    pattern_node,
    pattern_of,
    pattern_program,
    stack_problems,
)

__all__ = [
    "DEFAULT_FADE", "MIX", "PATTERN", "Compositor", "Controls", "Knob", "Layer", "LayerControls", "LayerError",
    "LiveLayer", "Look", "Resolved", "Route", "Section", "controls_of", "layer_address", "layer_seed",
    "pattern_layer", "pattern_node", "pattern_of", "pattern_program", "stack_problems",
]
