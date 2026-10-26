"""Output sinks: the engine's edge (see `pewpew.sinks.base` for the
contract and how sinks compose with `SinkDriver`)."""

from __future__ import annotations

from pewpew.sinks.ansi import AnsiLayout, AnsiSink
from pewpew.sinks.base import (
    DISPLAY_GAMMA,
    Controls,
    RateGate,
    Sink,
    to_display_u8,
    to_linear_u8,
)
from pewpew.sinks.ddp import Board, DdpSink, parse_board
from pewpew.sinks.preview import PreviewSink

__all__ = [
    "Sink",
    "Controls",
    "RateGate",
    "DISPLAY_GAMMA",
    "to_display_u8",
    "to_linear_u8",
    "AnsiLayout",
    "AnsiSink",
    "PreviewSink",
    "Board",
    "DdpSink",
    "parse_board",
]
