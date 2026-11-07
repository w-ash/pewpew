"""The capture node's wire format (pewpew.audio.wire) and its firmware's
side of it: the C header holds the same values, the portable C
(sha256.c, sub.c) built on this host signs and checks SUBs byte for byte
as Python does, and the committed packets pin the byte layout, sample
order included."""

from __future__ import annotations

import hashlib
import hmac
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from audio_signals import sine
from pewpew import wled
from pewpew.audio import wire
from pewpew.audio.wire import Denial, Packet

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "firmware" / "audio-node" / "main"
FIXTURES = Path(__file__).parent / "fixtures" / "audio_net"
TONE = FIXTURES / "tone-1khz-synthetic.bin"
KEY = bytes(range(32))
MAC = "aabbccddeeff"
NONCE = 0x0123_4567_89AB_CDEF
HOST = ("192.168.8.20", 50123)


# ---- one source of truth ---------------------------------------------------------


def header_values() -> dict[str, str]:
    text = (FIRMWARE / "wire.h").read_text()
    return dict(re.findall(r"^#define PP_(\w+) (.+)$", text, re.MULTILINE))


def test_the_c_header_holds_the_values_python_does() -> None:
    expected = {
        "PORT": wire.PORT, "RATE": wire.RATE, "SAMPLES": wire.SAMPLES, "MAX_SAMPLES": wire.MAX_SAMPLES,
        "VERSION": wire.VERSION, "AUDIO_MAGIC": wire.AUDIO_MAGIC.decode(), "SUB_MAGIC": wire.SUB_MAGIC.decode(),
        "REFUSAL_MAGIC": wire.REFUSAL_MAGIC.decode(), "HEADER_SIZE": wire.HEADER.size,
        "SUB_HEAD_SIZE": wire.SUB_HEAD.size, "TAG_SIZE": wire.TAG_SIZE, "SUB_SIZE": wire.SUB_SIZE,
        "REFUSAL_SIZE": wire.REFUSAL.size, "KEY_SIZE": wire.KEY_SIZE, "FLAG_CLIP": wire.CLIP,
        "FLAG_OVERFLOW": wire.OVERFLOW, "HOLD_MS": round(wire.HOLD_S * 1000), "BRAND": wled.NODE_BRAND,
        "PRODUCT": wire.PRODUCT, "FIRMWARE": wire.FIRMWARE,
        **{f"DENY_{d.name}": d.value for d in Denial},
    }
    found = {name: value.strip('"') for name, value in header_values().items()}
    assert found == {name: f"{value:#04x}" if name.startswith("FLAG") else str(value)
                     for name, value in expected.items()}
    assert (wire.HEADER.size + 2 * wire.MAX_SAMPLES) <= 1472  # one UDP payload at a 1 500-byte MTU


# ---- packets -----------------------------------------------------------------------


@given(st.integers(0, 2**64 - 1), st.integers(0, 2**64 - 1), st.integers(0, 255),
       st.lists(st.integers(-32768, 32767), min_size=1, max_size=wire.MAX_SAMPLES))
def test_a_packet_round_trips(index: int, nonce: int, flags: int, ints: list[int]) -> None:
    packet = Packet(index, nonce, flags, np.array(ints, "<i2").tobytes())
    data = wire.encode(packet)
    assert len(data) == 20 + 2 * len(ints) and wire.decode(data) == packet
    assert packet.end == index + len(ints) and packet.samples().dtype == np.float32


@pytest.mark.parametrize("data", [
    b"", b"PA" + bytes(18), b"PA" + bytes(19), b"PB\x01" + bytes(19), b"PA\x02" + bytes(19),
    b"PA\x01" + bytes(17) + b"\0" * (2 * wire.MAX_SAMPLES + 2), wire.refusal(Denial.KEY),
])
def test_anything_but_an_audio_packet_decodes_to_none(data: bytes) -> None:
    assert wire.decode(data) is None


def test_samples_round_to_s16_and_clip_as_the_converter_does() -> None:
    assert np.frombuffer(wire.pcm(np.array([0.0, 0.5, -1.0, 1.0, 2.0])), "<i2").tolist() == [
        0, 16384, -32768, 32767, 32767]


def tone_packets(data: bytes) -> list[Packet]:
    """The packets of a tone recording: whole datagrams of `SAMPLES` each."""
    size = wire.HEADER.size + 2 * wire.SAMPLES
    packets = [wire.decode(data[i:i + size]) for i in range(0, len(data), size)]
    assert all(packets) and len(data) % size == 0
    return [p for p in packets if p is not None]


def test_the_synthetic_tone_packets_pin_the_encoders_bytes(regen_goldens: bool) -> None:
    tone = sine(1000.0, 0.2, level=0.5)
    made = b"".join(wire.encode(Packet(48000 + 480 * k, NONCE, 0, wire.pcm(tone[480 * k:480 * (k + 1)])))
                    for k in range(20))
    if regen_goldens:
        TONE.parent.mkdir(parents=True, exist_ok=True)
        TONE.write_bytes(made)
    data = TONE.read_bytes()
    assert data == made
    assert data[:4] == b"PA\x01\x00" and data[4:12] == (48000).to_bytes(8, "little")
    assert np.abs(np.concatenate([p.samples() for p in tone_packets(data)]) - tone).max() <= 1 / 32768


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("tone-1khz*.bin")), ids=lambda p: p.name)
def test_a_tone_recording_holds_a_1_khz_tone_in_index_order(path: Path) -> None:
    # A node's own recording (bench/bench_node.py --tone) joins the synthetic one here.
    packets = tone_packets(path.read_bytes())
    assert len(packets) == 20 and [p.index - packets[0].index for p in packets] == [480 * k for k in range(20)]
    samples = np.concatenate([p.samples() for p in packets]).astype(np.float64)
    spectrum = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
    assert abs(np.argmax(spectrum[1:]) + 1 - 1000.0 * len(samples) / wire.RATE) <= 1  # the peak at 1 kHz


# ---- SUB ---------------------------------------------------------------------------


def sub(**kw) -> bytes:
    args = {"key": KEY, "mac": MAC, "nonce": NONCE, "address": HOST} | kw
    return wire.subscription(args["key"], args["mac"], args["nonce"], args["address"])


def check(data: bytes, **kw) -> Denial | None:
    args = {"mac": MAC, "nonce": NONCE, "key": KEY, "source": HOST} | kw
    return wire.check_subscription(data, **args)


def test_a_sub_signs_the_mac_nonce_and_reply_address() -> None:
    data = sub()
    assert len(data) == wire.SUB_SIZE and data[:3] == b"PS\x01" and data[3:9] == bytes.fromhex(MAC)
    assert data[23:] == hmac.new(KEY, data[:23], hashlib.sha256).digest()
    assert check(data) is None
    assert wire.subscription(KEY, "aa:bb:cc:dd:ee:ff", NONCE, HOST) == data


@pytest.mark.parametrize("data, kw, denial", [
    (sub()[:-1], {}, Denial.MALFORMED),
    (b"PX" + sub()[2:], {}, Denial.MALFORMED),
    (sub(mac="001122334455"), {}, Denial.OTHER_NODE),  # a node that took the old address after a DHCP move
    (sub(nonce=NONCE + 1), {}, Denial.STALE),  # signed before the node rebooted
    (sub(), {"source": ("192.168.8.21", HOST[1])}, Denial.ADDRESS),  # replayed from another host
    (sub(), {"source": (HOST[0], HOST[1] + 1)}, Denial.ADDRESS),
    (sub(), {"key": None}, Denial.NO_KEY),
    (sub(key=bytes(32)), {}, Denial.KEY),
])
def test_a_node_refuses_a_wrong_mac_nonce_reply_address_or_key(data: bytes, kw: dict, denial: Denial) -> None:
    assert check(data, **kw) is denial


def test_a_refusal_carries_its_denial() -> None:
    for denial in Denial:
        assert wire.refused(wire.refusal(denial)) is denial and denial in wire.DENIALS
    assert wire.refused(b"PR\x01\x63") is None and wire.refused(b"PR\x01") is None


def test_a_mac_is_twelve_hex_digits_with_or_without_colons() -> None:
    assert wire.mac_bytes("AA:BB:CC:DD:EE:FF") == wire.mac_bytes("aabbccddeeff") == bytes.fromhex(MAC)
    with pytest.raises(ValueError, match="not a MAC address"):
        wire.mac_bytes("aabbccddee")


# ---- the firmware's C, built on this host --------------------------------------------


@pytest.fixture(scope="module")
def node(tmp_path_factory: pytest.TempPathFactory):
    """The harness (tests/c/node_harness.c) over the firmware's portable C,
    as a running process: `ask(line)` returns its answer."""
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if cc is None:
        pytest.skip("no C compiler on this host")
    exe = tmp_path_factory.mktemp("node") / "node"
    subprocess.run([cc, "-std=c11", "-O0", "-Wall", "-Wextra", "-Werror", f"-I{FIRMWARE}", "-o", str(exe),
                    str(Path(__file__).parent / "c" / "node_harness.c"), str(FIRMWARE / "sha256.c"),
                    str(FIRMWARE / "sub.c")], check=True, capture_output=True)
    proc = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    assert proc.stdin is not None and proc.stdout is not None

    def ask(line: str) -> str:
        assert proc.stdin is not None and proc.stdout is not None
        proc.stdin.write(line + "\n")
        proc.stdin.flush()
        return proc.stdout.readline().strip()

    yield ask
    proc.stdin.close()
    proc.wait()
    proc.stdout.close()


@pytest.mark.parametrize("message", [b"", b"abc", b"a" * 55, b"a" * 56, b"a" * 64, bytes(range(256)) * 3])
def test_the_firmwares_sha256_is_fips_180_4s(node, message: bytes) -> None:
    assert node(f"sha {message.hex() or '-'}") == hashlib.sha256(message).hexdigest()


@given(st.binary(min_size=1, max_size=100), st.binary(max_size=200))
def test_the_firmwares_hmac_is_pythons(node, key: bytes, message: bytes) -> None:
    assert node(f"hmac {key.hex()} {message.hex() or '-'}") == hmac.new(key, message, hashlib.sha256).hexdigest()


def ip_hex(ip: str) -> str:
    return bytes(int(part) for part in ip.split(".")).hex()


def node_code(node, data: bytes, source: tuple[str, int], now_ms: int) -> int:
    return int(node(f"sub {data.hex()} {ip_hex(source[0])} {source[1]} {now_ms}"))


@pytest.mark.parametrize("data, kw, denial", [
    (sub()[:-1], {}, Denial.MALFORMED),
    (sub(mac="001122334455"), {}, Denial.OTHER_NODE),
    (sub(nonce=NONCE + 1), {}, Denial.STALE),
    (sub(), {"source": ("192.168.8.21", HOST[1])}, Denial.ADDRESS),
    (sub(), {"source": (HOST[0], HOST[1] + 1)}, Denial.ADDRESS),
    (sub(key=bytes(32)), {}, Denial.KEY),
    (sub(), {}, None),
])
def test_the_firmware_checks_a_sub_as_python_does(node, data: bytes, kw: dict, denial: Denial | None) -> None:
    assert node(f"init {MAC} {NONCE} {KEY.hex()}") == "ok"
    source = kw.get("source", HOST)
    assert node_code(node, data, source, 0) == (0 if denial is None else denial.value)
    assert check(data, **kw) is denial


def test_the_firmware_without_a_key_refuses_and_the_holder_keeps_the_stream(node) -> None:
    assert node(f"init {MAC} {NONCE} -") == "ok"
    assert node_code(node, sub(), HOST, 0) == Denial.NO_KEY
    node(f"init {MAC} {NONCE} {KEY.hex()}")
    other = ("192.168.8.21", 50200)
    assert node_code(node, sub(), HOST, 0) == 0
    assert node_code(node, sub(address=other), other, 2999) == Denial.HELD  # the holder renewed under 3 s ago
    moved = (HOST[0], HOST[1] + 7)  # the holder restarted under launchd: a new port at once
    assert node_code(node, sub(address=moved), moved, 2999) == 0
    assert node_code(node, sub(address=other), other, 2999 + 3000) == 0  # 3 s without a renewal frees it
