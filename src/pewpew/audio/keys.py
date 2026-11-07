"""The capture nodes' keys: one random 32-byte key per node, by MAC, that
signs each SUB (pewpew.audio.wire).

The host keeps them in one file only its owner can read, beside the audit
log: `~/.local/state/pewpew/audio-keys.json`, or `$PEWPEW_AUDIO_KEYS`;
never in the plist, argv, a log or the repo. A node gets its key once, at
flash time, in an NVS image: `csv` writes the CSV that ESP-IDF's
`nvs_create_partition_image` turns into it (firmware/audio-node), since
Improv defines no command to carry one (RA-28 §6). Making a key is
tier-1 bench work and attended (`python -m pewpew audio key MAC`).
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path

from pewpew import audit
from pewpew.audio.wire import KEY_SIZE, mac_bytes
from pewpew.jsonfile import write_atomic

ENV_VAR = "PEWPEW_AUDIO_KEYS"
VERSION = 1
NAMESPACE = "pewpew"  # the node reads its key from this NVS namespace (main.c)
SECRET = 0o600


def keys_path() -> Path:
    """Where the keys live: `$PEWPEW_AUDIO_KEYS`, else the per-user state dir."""
    return audit.state_file(ENV_VAR, "audio-keys.json")


def mac_text(mac: str) -> str:
    """`mac` as the key file and /json/info give it: 12 lowercase hex
    digits. Raises ValueError for text that is no MAC."""
    return mac_bytes(mac).hex()


def _read() -> dict[str, str]:
    path = keys_path()
    try:
        data = json.loads(path.read_bytes())
    except FileNotFoundError:
        return {}
    keys = data.get("keys") if isinstance(data, dict) else None
    if not isinstance(keys, dict):
        raise ValueError('the key file holds no {"keys": {...}}; fix or move it, then make each key again')  # noqa: TRY004  a bad file, not a caller error
    return {str(mac): str(key) for mac, key in keys.items()}


def load(mac: str) -> bytes | None:
    """The key of node `mac`, or None when the file has none. Raises
    ValueError for a file or an entry that is malformed, OSError for one
    that cannot be read."""
    text = _read().get(mac_text(mac))
    if text is None:
        return None
    key = bytes.fromhex(text) if len(text) == 2 * KEY_SIZE else b""
    if len(key) != KEY_SIZE:
        raise ValueError(f"the key file's entry for {mac_text(mac)} is not {KEY_SIZE} bytes of hex")
    return key


def ensure(mac: str) -> bytes:
    """The key of node `mac`, made and stored when the file has none. A
    node keeps its key through every reflash."""
    found = load(mac)
    if found is not None:
        return found
    key = secrets.token_bytes(KEY_SIZE)
    keys = {**_read(), mac_text(mac): key.hex()}
    path = keys_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, (json.dumps({"version": VERSION, "keys": keys}, indent=2) + "\n").encode(), mode=SECRET)
    return key


def csv(key: bytes) -> str:
    """The NVS CSV that holds `key` in the node's namespace."""
    return f"key,type,encoding,value\n{NAMESPACE},namespace,,\nkey,data,hex2bin,{key.hex()}\n"


def csv_path(mac: str) -> Path:
    """Where `audio key` writes the CSV: beside the key file."""
    return keys_path().with_name(f"audio-node-{mac_text(mac)}.csv")


def write_csv(mac: str, key: bytes) -> Path:
    """Write the CSV for node `mac`, readable by its owner only; returns its path."""
    path = csv_path(mac)
    write_atomic(path, csv(key).encode(), mode=SECRET)
    return path


__all__ = ["ENV_VAR", "csv", "csv_path", "ensure", "keys_path", "load", "mac_text", "write_csv"]
