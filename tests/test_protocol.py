"""Hardware-independent BLE protocol regression tests."""
import base64
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "jackery_protocol",
    Path(__file__).resolve().parents[1] / "custom_components/jackery_p1/protocol.py",
)
protocol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(protocol)

KEY = bytes(range(16))


def test_modbus_crc_known_vector():
    assert protocol.crc16(b"123456789").hex() == "374b"


@pytest.mark.parametrize("command,expected", [
    ("read_wifi", (4001, 1)),
    ("read_timezone", (4004, 22)),
    ("read_device_info", (4005, 106)),
])
def test_read_command_packet_roundtrip(command, expected):
    packet = protocol.read_command_packet(KEY, command)
    assert packet[:16] != bytes(16)
    decoded = protocol.decrypt_frame(KEY, packet)
    result = protocol.Reassembler().add(decoded)
    assert (result["actionId"], result["bleMsgType"]) == expected
    assert result["body"] == {"cmd": expected[1]}


def test_read_info_alias():
    result = protocol.Reassembler().add(
        protocol.decrypt_frame(KEY, protocol.read_info_packet(KEY))
    )
    assert result["body"] == {"cmd": 106}


@pytest.mark.parametrize("name", ["write_wifi", "restore_mqtt", "unknown", "4"])
def test_unknown_or_write_commands_refused(name):
    with pytest.raises(KeyError):
        protocol.read_command_packet(KEY, name)


@pytest.mark.parametrize("size", [16, 24, 32])
def test_base64_aes_key_lengths(size):
    raw = bytes(range(size))
    assert protocol.decode_key(base64.b64encode(raw).decode()) == raw


@pytest.mark.parametrize("encoded", ["not base64!", "", "YQ==", "SGVsbG8="])
def test_invalid_aes_keys_rejected(encoded):
    with pytest.raises(ValueError):
        protocol.decode_key(encoded)


def test_tampered_ciphertext_rejected():
    packet = bytearray(protocol.read_info_packet(KEY))
    packet[-1] ^= 0xFF
    with pytest.raises(ValueError):
        protocol.decrypt_frame(KEY, bytes(packet))


@pytest.mark.parametrize("packet", [b"", b"test", b"\0" * 31, b"\0" * 33])
def test_invalid_encrypted_packet_lengths(packet):
    with pytest.raises(ValueError):
        protocol.decrypt_frame(KEY, packet)


def test_crc_rejects_corrupted_plaintext():
    payload = b'{"cmd":106}'
    header = b"".join(x.to_bytes(2, "big") for x in (1, 1, 4005, 106, len(payload)))
    bad = b"DFED" + header + payload
    with pytest.raises(ValueError, match="signature"):
        _decrypt_modified(bad)


def _decrypt_modified(frame):
    # Build a valid ciphertext with a bad DFED signature: CRC stays valid.
    return protocol.decrypt_frame(KEY, protocol.encrypt_frame(KEY, b"XXXX" + frame[4:]))


def test_fragment_reassembly_out_of_order():
    raw = b'{"cmd":106,"power":-14,"volt1":239}'
    parts = [raw[:8], raw[8:16], raw[16:]]
    parser = protocol.Reassembler()
    def frame(page):
        fragment = parts[page - 1]
        header = b"".join(x.to_bytes(2, "big") for x in (page, 3, 4005, 106, len(fragment)))
        return header + fragment
    assert parser.add(frame(2)) is None
    assert parser.add(frame(1)) is None
    result = parser.add(frame(3))
    assert result["body"] == json.loads(raw)
    assert parser.pages == {}


@pytest.mark.parametrize("page,count,length,body", [
    (0, 1, 2, b"{}"),
    (2, 1, 2, b"{}"),
    (1, 0, 2, b"{}"),
    (1, 129, 2, b"{}"),
    (1, 1, 30, b"{}"),
])
def test_reject_invalid_fragments(page, count, length, body):
    header = b"".join(x.to_bytes(2, "big") for x in (page, count, 4005, 106, length))
    with pytest.raises(ValueError):
        protocol.Reassembler().add(header + body)


def test_response_payload_preserves_zero_negative_and_optional_fields():
    observed = {"cmd": 106, "volt1": 239, "curr1": 40, "power1": -17,
                "power": -14, "freq": 50, "power2": 0}
    data = json.dumps(observed, separators=(",", ":")).encode()
    header = b"".join(x.to_bytes(2, "big") for x in (1, 1, 4005, 106, len(data)))
    result = protocol.Reassembler().add(header + data)
    assert result["body"] == observed
