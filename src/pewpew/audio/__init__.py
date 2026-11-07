"""Audio input: sources, the analysis on the sample clock, and the feature
sources a run reads (ADR-009, 2026-11-06 amendments; RA-28).

    source (a WAV file, an array, an input of this computer, a capture
            node, a replayed packet trace)
      -> Analyser: hops, levels and onsets on the sample clock
      -> Tracker: tempo and beats (Stark, Davies & Plumbley 2009)
      -> Oscillator: `beat_phase` on engine time, steered by a PLL
      -> AudioFeatures: the frame for each tick, a `FeatureSource`

`ReplayFeatures` plays back what `FeatureLog` wrote. Without `--audio`, a
run reads `FakeFeatures` as before. Nothing here imports a capture
library: `DeviceSource` imports sounddevice (`pewpew[audio]`) only when an
input is listed or opened (pewpew.audio.device); a capture node needs only
the standard library's socket and hmac (pewpew.audio.net).
"""

from __future__ import annotations

from pewpew.audio.analysis import HOP_S, LOST_S, Analyser, Hop, Levels
from pewpew.audio.beat import Oscillator, Tracker
from pewpew.audio.clock import SampleClock
from pewpew.audio.device import DeviceSource
from pewpew.audio.features import AudioFeatures, FeatureLog, ReplayFeatures
from pewpew.audio.net import NetSource, TraceSource
from pewpew.audio.source import ArraySource, AudioSource, Block, LiveSource, read_wav

__all__ = [
    "HOP_S", "LOST_S", "Analyser", "ArraySource", "AudioFeatures", "AudioSource", "Block", "DeviceSource",
    "FeatureLog", "Hop", "Levels", "LiveSource", "NetSource", "Oscillator", "ReplayFeatures", "SampleClock",
    "TraceSource", "Tracker", "read_wav",
]
