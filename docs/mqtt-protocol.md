# Jackery P1 MQTT protocol (research)

> Observed in **UART firmware logs during a successful connection to Jackery's official broker**, rather than decrypted network traffic. Unofficial, incomplete specification. See [overview](reverse-engineering.md).

## Endpoint and topics

Observed official endpoint: `mqtts://dev.jackeryapp.com:8883` (TLS).

```text
dh/device/<serial>/action   cloud → device; commands/config
dh/device/<serial>/status   device → cloud; meter telemetry
dh/device/<serial>/event    device → cloud; events/counters/acknowledgements
dh/device/<serial>/alert    topic generated; payload unknown
dh/device/<serial>/log      topic generated; payload unknown
```

Device serial and authentication details are deliberately omitted.

## Observed message types

| Type | Observation | Direction |
|---|---|---|
| 2 | Measurement status and incremental updates | Device → cloud |
| 8 | Firmware version | Device → cloud |
| 9 | Startup event (null body); exact semantics unknown | Device → cloud |
| 16 | Energy counters `engy` and `engyo` | Device → cloud |
| 17 | Reporting configuration | Cloud → device |
| 18 | Config acknowledgement | Device → cloud |
| 25 | Wrapper for `cmd:106` | Cloud → device |
| 45 | Wrapper for `cmd:3` timezone setting | Cloud → device |
| 100 | Wrapper for `cmd:110`; purpose unknown | Cloud → device |

Envelopes may contain `deviceType` (observed 9), `type`, `messageId`, `eventId`, `body`, `ts`. Field presence depends on direction and message type.

## Status payloads and deltas

Initial type-2 status included device network metadata (SSID, MAC, IP, RSSI) plus voltage, current and power values. A sanitized example excluding identifying fields:

```json
{"deviceType":9,"type":2,"messageId":5,"body":{"rssi":-76,"volt1":237,"volt2":0,"volt3":0,"curr1":40,"curr2":0,"curr3":0,"curr":0,"power1":0,"power2":0,"power3":0,"power":0},"ts":1792175248}
```

Subsequent status messages can contain *only changed fields*:

```json
{"deviceType":9,"type":2,"messageId":12,"body":{"rssi":-79,"volt1":238,"power1":221,"power":223},"ts":1792175257}
```

A decoder must merge each `body` into cached state, not interpret omitted measurements as zero. Consider stale-state invalidation on disconnect.

## Counters

Observed type-16 event:

```json
{"deviceType":9,"type":16,"messageId":8,"body":{"engy":30713,"engyo":480},"ts":1792175249}
```

The scaling, units and precise import/export meanings of `engy` and `engyo` are **unverified**.

## Reporting configuration

The official service sent type-17 configuration with fields:

```json
{"type":17,"body":{"interval":4,"statisticInterval":600,"logInterval":3,"logCount":100,"preDownloadEnable":1,"preDownloadStart":2,"preDownloadEnd":6}}
```

The firmware replied with type 18; the acknowledgement's `eventId` correlated to the incoming config message's `messageId`. Cloud requests alternated `interval` values **4** and **300**; telemetry was about four seconds apart with `interval:4`. What triggers these changes is not proven.

## TLS experiment and limitations

A user-controlled Mosquitto TLS endpoint configured through BLE was contacted but server certificate verification failed (`mbedtls_ssl_handshake returned -0x2700`). Connecting to the official Jackery endpoint succeeded. This does **not** prove certificate pinning, and the firmware's trusted CA bundle remains unidentified.

Unresolved: MQTT credential derivation and session semantics, full `/alert` and `/log` messages, some command types, energy scaling, and a cloud-compatible local MQTT proxy.

**Security:** Never publish raw UART logs containing Wi-Fi, MQTT, device serial, MAC, tokens or BLE key material.
