"""What `run --audio SPEC` names, read and checked at launch.

    NAME               one of this computer's inputs (`audio list`), by its
                       exact name, its index or a part of its name
                       (pewpew.audio.device; needs pewpew[audio])
    net:NODE           a capture node by its name or IPv4 address
                       (pewpew.audio.net); outside --unattended, with
                       --allow-host IP
    FILE.wav           a WAV file, analysed live and played on a loop;
                       so is any existing file, and any spec with a path
                       separator, which names a file and never an input
    replay:PATH.jsonl  a feature log (`--feature-log`), played back

A missing or unreadable file is refused, as are a blank spec, the default
input, a name that fits several inputs, a malformed node name, and a node
outside `--unattended` without an `--allow-host` that names its address. An
input that is not plugged in, or a node that is not on, is not refused:
the run starts lost and opens it once it appears. A refusal names the
cause and never the path, which the caller adds.
"""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

from pewpew.audio.device import device_source
from pewpew.audio.features import ReplayFeatures
from pewpew.audio.net import PREFIX as NET
from pewpew.audio.net import node_source
from pewpew.audio.source import ArraySource, AudioSource, read_wav

REPLAY = "replay:"


def read_input(
    spec: str, *, fps: float, channel: int | None = None, unattended: bool = False, allow_hosts: Collection[str] = (),
    bind: str | None = None,
) -> AudioSource | ReplayFeatures:
    """The source or the replay `spec` names, for a loop at `fps`, reading
    one `channel` (numbered from 0) or the mean of all. A node is
    subscribed to by an unattended run (`unattended`) or one of `allow_hosts`, from the
    address `bind` when given. Raises ValueError naming the cause."""
    if spec.startswith(REPLAY):
        path = Path(spec.removeprefix(REPLAY))
        try:
            return ReplayFeatures(path)
        except OSError as exc:
            raise ValueError(f"cannot read the feature log: {exc.strerror or exc}") from None
        except ValueError as exc:
            raise ValueError(f"not a feature log: {exc}") from None
    if spec.startswith(NET):
        return node_source(spec.removeprefix(NET), fps=fps, unattended=unattended, allow_hosts=allow_hosts, bind=bind)
    path = Path(spec)
    if path.suffix.lower() == ".wav" or path.is_file() or len(path.parts) > 1:
        return wav_source(path, loop=True, channel=channel)
    return device_source(spec, fps=fps, channel=channel)


def wav_source(path: Path, *, loop: bool = False, channel: int | None = None) -> ArraySource:
    """The samples of the WAV file at `path`, one `channel` or the mean of
    all, as a source; ValueError naming the cause."""
    try:
        samples, rate = read_wav(path, channel)
    except OSError as exc:
        raise ValueError(f"cannot read the WAV file: {exc.strerror or exc}") from None
    return ArraySource(samples, rate, name=path.name, kind="file", loop=loop)


__all__ = ["NET", "REPLAY", "read_input", "wav_source"]
