"""Accessory BLE framing and AES-CBC protocol, validated against P1 hardware."""
from __future__ import annotations
import base64
import json
import secrets
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def decode_key(value: str) -> bytes:
    key = base64.b64decode(value.strip(), validate=True)
    if len(key) not in (16, 24, 32):
        raise ValueError("Invalid Bluetooth AES key length")
    return key

def crc16(data: bytes) -> bytes:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc.to_bytes(2, "little")

def encrypt_frame(key: bytes, frame: bytes) -> bytes:
    clear = frame + secrets.token_bytes(2)
    clear += crc16(clear)
    iv = secrets.token_bytes(16)
    padder = padding.PKCS7(128).padder()
    clear = padder.update(clear) + padder.finalize()
    enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return iv + enc.update(clear) + enc.finalize()

def decrypt_frame(key: bytes, packet: bytes) -> bytes:
    if len(packet) < 32 or (len(packet) - 16) % 16:
        raise ValueError("Invalid encrypted packet size")
    dec = Cipher(algorithms.AES(key), modes.CBC(packet[:16])).decryptor()
    clear = dec.update(packet[16:]) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    clear = unpadder.update(clear) + unpadder.finalize()
    if not clear.startswith(bytes.fromhex("DFED")) or crc16(clear[:-2]) != clear[-2:]:
        raise ValueError("Invalid DFED signature or CRC")
    return clear[2:-4]

READ_COMMANDS = {"read_wifi": (4001, 1), "read_timezone": (4004, 22), "read_device_info": (4005, 106)}

def read_command_packet(key: bytes, command: str) -> bytes:
    action, kind = READ_COMMANDS[command]
    body = json.dumps({"cmd": kind}, separators=(",", ":")).encode()
    frame = bytes.fromhex("DFED") + b"".join(x.to_bytes(2, "big") for x in (1, 1, action, kind, len(body))) + body
    return encrypt_frame(key, frame)

def read_info_packet(key: bytes) -> bytes:
    return read_command_packet(key, "read_device_info")

class Reassembler:
    def __init__(self) -> None:
        self.pages: dict[tuple[int, int, int], dict[int, bytes]] = {}

    def add(self, payload: bytes) -> dict | None:
        if len(payload) < 10:
            raise ValueError("Short BLE frame")
        page, count, action, kind, length = (int.from_bytes(payload[i:i + 2], "big") for i in range(0, 10, 2))
        chunk = payload[10:]
        if not 1 <= count <= 128 or not 1 <= page <= count or len(chunk) != length:
            raise ValueError("Invalid BLE frame header")
        token = (action, kind, count)
        pages = self.pages.setdefault(token, {})
        pages[page] = chunk
        if len(pages) < count:
            return None
        try:
            body = json.loads(b"".join(pages[i] for i in range(1, count + 1)))
        finally:
            del self.pages[token]
        return {"actionId": action, "bleMsgType": kind, "body": body}
