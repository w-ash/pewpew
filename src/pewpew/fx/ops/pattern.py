"""The `pattern` op: a hand-written pattern as a source node.

A layer that runs one pattern node runs its pattern directly, in the
layer's own renderer, fixture units included (ADR-021). Inside a program
with other nodes, a pattern node renders at the program's points, so it
takes only a pixel-unit pattern, and only a warpable one under a coord op
(ADR-022; pewpew.fx.compile checks both). Its knobs are the pattern's own
params; its `pattern` arg names the pattern and is not a knob.

The op keeps the pattern's contract: `before_render` once per frame, a
pure `render` with the pattern's buffers read-only, and `self.pixels` the
pattern's own last frame.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from pewpew.fx.graph import PATTERN
from pewpew.fx.op import BindCtx, Cost, FrameCtx, Op, Resolve
from pewpew.fx.types import Coords, Fn, Sig, Ty
from pewpew.pattern import Inheritance, Pattern


class PatternOp(Op, op=PATTERN):
    """Runs a pattern (gallery name, or a pattern file's name) as a source:
    its frame at the program's points. Its knobs are the pattern's params."""

    sig = Sig.SOURCE
    out = Ty.RGB
    examples = ('pattern("plasma").kaleid(5)', 'pattern("wave").hue(60)')
    cost = Cost(40.0, 20.0)

    def __init__(self, cls: type[Pattern]) -> None:
        super().__init__()
        self.inner = cls()
        self.last: np.ndarray | None = None
        self._inherit: Inheritance | None = None

    @classmethod
    def make(cls, args: Mapping[str, Any], resolve: Resolve) -> Op:
        spec = args.get(PATTERN)
        found = resolve(spec) if isinstance(spec, str) else None
        if found is None:
            raise ValueError(f"no pattern {spec!r} to run")
        return cls(found)

    @classmethod
    def knob_class(cls, args: Mapping[str, Any], resolve: Resolve | None) -> type | None:
        spec = args.get(PATTERN)
        return resolve(spec) if resolve is not None and isinstance(spec, str) else None

    @classmethod
    def knob_values(cls, args: Mapping[str, Any]) -> dict[str, Any]:
        return {name: value for name, value in args.items() if name != PATTERN}

    @classmethod
    def warps(cls, args: Mapping[str, Any], resolve: Resolve | None) -> bool:
        found = cls.knob_class(args, resolve)
        return found is None or bool(getattr(found, "warpable", False))

    @property
    def target(self) -> object:
        return self.inner

    def adopt(self, old: Op) -> None:
        super().adopt(old)
        if isinstance(old, PatternOp):
            self._inherit = Inheritance(old.inner)
            self.last = old.last

    def setup(self, ctx: BindCtx) -> None:
        super().setup(ctx)
        if self._inherit is None:
            self.last = None  # a rebind starts from the pattern's zeroed pixels, as every buffer does
        c = ctx.coords
        try:
            self.inner._bind(ctx.n, c.x, c.y, c.z, c.index, seed=ctx.seed, params=dict(ctx.values),
                             inherit=self._inherit, name=ctx.path)
        finally:
            self._inherit = None

    def advance(self, ctx: FrameCtx, inputs: Sequence[Fn]) -> None:
        if self.last is not None:
            self.inner.pixels = self.last
        self.inner.before_render(ctx.dt, ctx.features)

    def build(self, inputs: Sequence[Fn]) -> Fn:
        def pattern(c: Coords) -> np.ndarray:
            locked, _ = self.inner._lock_buffers()
            try:
                frame = self.inner.render(c.x, c.y, c.z, c.index)
            finally:
                self.inner._unlock_buffers(locked)
            self.last = frame.copy()  # the pattern's `pixels` next frame, as the renderer keeps it
            return frame

        return pattern
