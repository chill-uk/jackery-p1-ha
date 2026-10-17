# Jackery Smart Meter P1 — Reverse Engineering Notes

> Unofficial community research, not affiliated with Jackery. Findings reflect observed behaviour on one P1 and may vary by firmware. **Confirmed** means observed in a capture, measurement, or working implementation; **inferred** means plausible but not independently demonstrated; **unknown** means not yet established.

## Purpose and status

The goal is local Home Assistant monitoring while retaining the original device firmware and, ideally, official app functionality. The [Home Assistant integration](../README.md) already polls electrical telemetry locally via encrypted BLE. MQTT bridging and firmware backup remain research projects.

## Hardware and serial access

**Confirmed:** The examined P1 uses an ESP32-C3-MINI-1U. Firmware logs identify project `HB_P1`, ESP-IDF 5.3.3, application version `V1.01.112`, and 4 MB flash. A labelled test-pad group, in observed top-to-bottom order, is:

```text
V3.3
[unlabelled]
GND
EN
GPIO0
U0RXD
U0TXD
```

For **read-only** logging, connect P1 `U0TXD` to a **3.3 V logic** USB-UART adapter's RX, and GND to GND. Power the P1 normally from a safe, isolated supply; **do not connect the adapter's 3.3 V power output**. A bidirectional connection additionally requires adapter TX to P1 `U0RXD`. Never connect exposed mains-referenced circuitry to a computer.

Observed serial settings: **115200 baud, 8N1**. Example on macOS (adjust the device path):

```sh
cd ~/jackery-ble
screen -L /dev/cu.usbserial-A50285BI 115200
```

The older macOS GNU Screen version records to `screenlog.0` in the working directory. Raw logs can include **Wi-Fi passwords, MQTT credentials, tokens, serials, and MAC addresses**: sanitize before sharing.

**Confirmed:** Briefly pulling the labelled `EN` pad low on the safely isolated board resets the ESP32. A captured reset showed:

```text
ESP-ROM:esp32c3-eco7-20230720
rst:0x1 (POWERON),boot:0xf (SPI_FAST_FLASH_BOOT)
```

This is **normal flash boot**, not ROM download mode. Attempts to run `esptool flash-id` with both `--before no-reset` and `--before default-reset` returned `No serial data received`. **No firmware dump has been obtained**; flash encryption/security status is unknown.

**Unresolved PCB tracing:** An unlabelled pad was measured at approximately 3.3 V while powered and associated with 10 kΩ resistors R9, R12, and R14. A 10 kΩ path was observed to EN through R9; C8 appears associated with the reset network. **The unlabelled pad is not identified as GPIO9. Do not ground it on that assumption.** GPIO0 is not the ESP32-C3's normal ROM-download strapping pin; GPIO9 is relevant.

## BLE protocol

**Confirmed from Android-app analysis, BLE captures, and working integration:**

| Item | Value |
| --- | --- |
| GATT service | `0000bdee-0000-1000-8000-00805f9b34fb` |
| Write characteristic | `0000ee01-0000-1000-8000-00805f9b34fb` |
| Notify characteristic | `0000ee02-0000-1000-8000-00805f9b34fb` |
| Framing | Custom `DFED` packets, fragmentation and CRC16 |
| Encryption | AES-CBC with device-specific key; IV and padding handled by integration |
| Live measurement command | `106` |

Observed commands:

| Command | Observation |
| --- | --- |
| `1` | Wi-Fi scan |
| `2` | Wi-Fi and MQTT host/port provisioning (**write**) |
| `3` | Time-zone configuration (**write**) |
| `22` | Read time-zone information |
| `106` | Electrical measurement read |
| `107` | Meter notifications observed in provisioning capture |

Example **sanitized** measurement response (representative fields; values illustrative):

```json
{"cmd":106,"volt1":239,"curr1":40,"power1":-17,"power":-14}
```

The integration polls command 106 locally, normally every five seconds. Current values are scaled by 0.1 to amperes in the integration; signed power interpretation and optional fields require further validation. Device-specific BLE keys must never be committed.

## MQTT: observed cloud protocol

**Confirmed:** BLE provisioning command 2 can set the MQTT hostname and port. The device normally connects to `dev.jackeryapp.com:8883` using MQTT over TLS. The following device-scoped topics were logged (placeholder serial):

```text
dh/device/<serial>/action
dh/device/<serial>/status
dh/device/<serial>/event
dh/device/<serial>/alert
dh/device/<serial>/log
```

The `action` topic carried cloud-to-device commands; outgoing status and event traffic included telemetry and acknowledgements. The exact usage of `alert` and `log` has not been established.

Observed message types (do not assume this list is exhaustive):

| Type | Observed purpose |
| --- | --- |
| `2` | Meter/connectivity status, including live power/voltage/current |
| `8` | Firmware information |
| `16` | Energy counters (`engy`, `engyo`); units/scaling **unknown** |
| `17` | Cloud reporting configuration |
| `18` | Configuration acknowledgement |
| `25` | Cloud meter command, including command 106 |
| `45` | Cloud time-zone command, including command 3 |
| `100` | Cloud command including 110; purpose **unknown** |

Representative **sanitized** status payload:

```json
{
  "deviceType": 9,
  "type": 2,
  "messageId": 12,
  "body": {"rssi": -79, "volt1": 238, "power1": 221, "power": 223},
  "ts": 1792175257
}
```

**Confirmed:** After a full status message, the P1 publishes **partial/delta status updates** containing only changed fields. A consumer must merge the `body` into cached state; absent fields do not imply zero.

A captured cloud configuration included:

```json
{
  "type": 17,
  "eventId": 0,
  "body": {
    "interval": 4,
    "statisticInterval": 600,
    "logInterval": 3,
    "logCount": 100,
    "preDownloadEnable": 1,
    "preDownloadStart": 2,
    "preDownloadEnd": 6
  }
}
```

The P1 acknowledged reporting configurations with type 18. Values of `interval` **4** and **300** were observed. **Inferred:** a live view in the official app may be related to the shorter reporting interval; the triggering mechanism has not been proven.

## TLS and local broker experiment

**Confirmed:** The P1 initiated TLS when provisioned to a local Mosquitto broker. Even with a Let's Encrypt certificate and matching hostname, the P1 rejected the handshake:

```text
mbedtls_ssl_handshake returned -0x2700
Failed to verify peer certificate!
```

This is an X.509 certificate verification failure. Reprovisioning the official endpoint succeeded, including MQTT subscription, publication, and incoming cloud commands.

**Unknown:** The device's trusted CA store, certificate-pinning behaviour (if any), MQTT authentication derivation, and whether a trusted local TLS-terminating proxy is feasible. A DNS override alone cannot bypass certificate verification.

## Other firmware observations

- **Confirmed:** Boot logs report an HTTP server starting on TCP port 80. The root URL did not yield a useful response; routes and server lifetime remain unknown.
- **Confirmed:** Logs reference `eastron_first_task` and meter identification. **Inferred:** a dedicated meter communication component exists; its physical bus/protocol is unverified.
- **Confirmed:** Logs include `dh_p1_factory: Invalid factory mode command format`. This does **not** establish that the factory parser accepts commands on UART0.
- **Confirmed:** Pressing Enter via Screen/miniterm, including CRLF, did not reveal a text console. UART0 is demonstrably a diagnostic output; interactive shell support is unproven.

## Open questions / next experiments

1. Identify GPIO9 safely from a board schematic or verified trace, then inspect ROM download-mode security settings and attempt a **read-only** flash backup if permitted.
2. Determine the trusted MQTT CA(s) without exposing device secrets or weakening certificate verification.
3. Verify `engy`/`engyo` units against independent meter readings.
4. Identify the local HTTP endpoints, if any, and their authentication requirements.
5. Determine the metering interface and whether a local MQTT bridge can preserve official cloud behaviour.

## Responsible disclosure and contribution

Publish **redacted** captures only. Never commit raw UART logs, Wi-Fi credentials, BLE AES keys, MQTT usernames/passwords, access tokens, full firmware images, or device identifiers. Clearly distinguish measurements from interpretations, include firmware versions with findings, and use GitHub issues for independently reproduced discoveries.
