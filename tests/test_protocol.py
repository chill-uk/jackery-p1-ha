"""Protocol checks independent of Home Assistant runtime."""
import base64
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("jackery_protocol", Path(__file__).resolve().parents[1] / "custom_components/jackery_p1/protocol.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_modbus_crc():
    assert module.crc16(b"123456789").hex().upper() == "374B"

def test_round_trip():
    key = bytes(range(16))
    packet = module.read_info_packet(key)
    decoded = module.decrypt_frame(key, packet)
    result = module.Reassembler().add(decoded)
    assert result["actionId"] == 4005
    assert result["bleMsgType"] == 106
    assert result["body"] == {"cmd": 106}
    assert module.decode_key(base64.b64encode(key).decode()) == key

def test_fragment_reassembly():
    payload = b'{"power":-14}'
    parser = module.Reassembler()
    for index, part in enumerate((payload[:5], payload[5:]), 1):
        header = b"".join(x.to_bytes(2, "big") for x in (index, 2, 4005, 106, len(part)))
        response = parser.add(header + part)
    assert response["body"]["power"] == -14
