"""One-time Jackery login; only the device BLE key is returned."""
import base64
import json
import secrets
import uuid
from aiohttp import ClientSession, ClientTimeout, ClientError
from cryptography.hazmat.primitives import padding, serialization
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from .protocol import decode_key

HOST = "https://iot.jackeryapp.com/v1/"
PUBLIC_KEY_B64 = (
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCVmzgJy/4XolxPnkfu32YtJqYGFLYqf9/"
    "rnVgURJED+8J9J3Pccd6+9L97/+7COZE5OkejsgOkqeLNC9C3r5mhpE4zk/HStss7Q8/"
    "5DqkGD1annQ+eoICo3oi0dITZ0Qll56Dowb8lXi6WHViVDdih/oeUwVJY89uJNtTWrz7t7QIDAQAB"
)

class LoginError(Exception):
    """Login failed."""

class DeviceListError(Exception):
    """Device discovery failed."""

def encrypt_login(payload):
    """Match APK 2.4.3: AES-192 ECB of JSON, RSA encryption of ASCII key."""
    aes_string = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
    key = aes_string.encode("ascii")
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    padder = padding.PKCS7(128).padder()
    padded = padder.update(raw) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    encrypted = cipher.update(padded) + cipher.finalize()
    rsa_key = serialization.load_der_public_key(base64.b64decode(PUBLIC_KEY_B64))
    encrypted_key = rsa_key.encrypt(key, rsa_padding.PKCS1v15())
    return {
        "aesEncryptData": base64.b64encode(encrypted).decode("ascii"),
        "rsaForAesKey": base64.b64encode(encrypted_key).decode("ascii"),
    }

async def fetch_bound_p1_keys(email, password, region="NL"):
    """Fetch bound model 4001 devices; credentials and token remain ephemeral."""
    login = {
        "registerAppId": "com.hbxn.jackery",
        "macId": str(uuid.uuid4()),
        "account": email,
        "loginType": 2,
        "password": password,
        "regionCode": region.upper(),
    }
    headers = {
        "Accept-Language": "en-US", "platform": "android",
        "app_version": "2.4.3", "app_version_code": "102",
        "network": "wifi", "token": "",
    }
    try:
        async with ClientSession(timeout=ClientTimeout(total=25)) as session:
            # APK sends form-encoded fields, not JSON.
            async with session.post(HOST + "auth/login", data=encrypt_login(login), headers=headers) as response:
                if response.status != 200:
                    raise LoginError()
                result = await response.json(content_type=None)
            if not isinstance(result, dict) or result.get("code") != 0 or not result.get("token"):
                raise LoginError()
            headers["token"] = result["token"]
            async with session.get(HOST + "device/bind/list", headers=headers) as response:
                if response.status != 200:
                    raise DeviceListError()
                data = await response.json(content_type=None)
            if not isinstance(data, dict) or data.get("code") != 0 or not isinstance(data.get("data"), list):
                raise DeviceListError()
            devices = []
            for device in data["data"]:
                if not isinstance(device, dict) or device.get("modelCode") != 4001:
                    continue
                key = device.get("bluetoothKey")
                if not isinstance(key, str):
                    continue
                try:
                    decode_key(key)
                except ValueError:
                    continue
                devices.append({
                    "name": str(device.get("devNickname") or device.get("devModel") or "Jackery P1"),
                    "serial": str(device.get("devSn") or ""),
                    "bluetooth_key": key,
                })
            return devices
    except (ClientError, TimeoutError, ValueError, UnicodeError):
        raise LoginError() from None
