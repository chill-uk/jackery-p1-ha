# Jackery P1 Smart Meter for Home Assistant

[![GitHub release](https://img.shields.io/github/release/chill-uk/jackery-p1-ha?include_prereleases=&sort=semver&color=blue)](https://github.com/chill-uk/jackery-p1-ha/releases/)
[![Validation](https://github.com/chill-uk/jackery-p1-ha/actions/workflows/validate.yml/badge.svg)](https://github.com/chill-uk/jackery-p1-ha/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub issues](https://img.shields.io/github/issues/chill-uk/jackery-p1-ha)](https://github.com/chill-uk/jackery-p1-ha/issues)
[![GitHub downloads](https://img.shields.io/github/downloads/chill-uk/jackery-p1-ha/total)](https://github.com/chill-uk/jackery-p1-ha/releases/)

A **local Bluetooth integration** for the **Jackery Smart Meter P1 Reader (model 4001)**. It reads power, voltage and current measurements directly into Home Assistant without using Jackery's cloud API for ongoing telemetry.

The P1 uses encrypted Bluetooth communication. During setup, you can either retrieve its device-specific Bluetooth key with a **one-time Jackery account sign-in** or provide a key you already have.

> [!IMPORTANT]
> This is an **unofficial community integration**, not affiliated with or supported by Jackery.
>
> The project is still under development. Import/export power sign conventions and some optional measurement units are being validated.

## Features

- **Local electrical measurements** over encrypted BLE, polled approximately every **5 seconds**.
- **Total and per-phase power, voltage and current** sensors, where supplied by the meter.
- **Optional additional measurements** and Bluetooth diagnostics.
- **Read-only Home Assistant actions** for Wi-Fi scanning, time-zone information and meter readings.
- **No ongoing Jackery cloud dependency for telemetry** after the Bluetooth key has been obtained.

## Requirements

- A **Jackery Smart Meter P1 Reader (model 4001)**.
- Home Assistant with a working Bluetooth adapter or an **active, connectable Bluetooth proxy** in range of the P1.
- The device's **Base64-encoded Bluetooth AES key**, provided directly or retrieved during setup using a Jackery account with the P1 bound to it.

## Installation

### HACS (recommended)

[![Add to HACS via My Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=chill-uk&repository=jackery-p1-ha&category=integration)

1. Add this repository as a **custom integration** in [HACS](https://www.hacs.xyz/), using the button above or the repository URL.
2. Install **Jackery P1 (Local Bluetooth)**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**, then select **Jackery P1 (Local Bluetooth)**.
5. Follow the [configuration](#configuration) steps below.

> [!NOTE]
> The HACS distribution uses the `jackery_p1.zip` asset attached to a tagged GitHub release. If no compatible release asset is available, use [manual installation](#manual-installation).

### Manual installation

1. Download `jackery_p1.zip` from the [latest release](https://github.com/chill-uk/jackery-p1-ha/releases/latest), if available, **or** copy the [`custom_components/jackery_p1`](custom_components/jackery_p1) directory from this repository.
2. Place the integration files in `<config>/custom_components/jackery_p1/` in your Home Assistant configuration directory. If using the ZIP, its contents are the **integration files**, not a nested `jackery_p1` directory.
3. Restart Home Assistant.
4. Add **Jackery P1 (Local Bluetooth)** from **Settings → Devices & services**.

## Configuration

Choose one of two setup methods:

| Setup method | When to use it |
| --- | --- |
| **Jackery account** | Your P1 is bound to your Jackery account and you want the integration to retrieve its Bluetooth key once. Provide your account credentials and two-letter region code (default: `NL`). |
| **Existing Bluetooth key** | You already have the device's Base64 AES key and want to configure the integration without account sign-in. |

The integration stores the device's **Bluetooth address and AES key**, but **does not store your Jackery password or account session token**. Treat the key as sensitive and never include it in public logs or issue reports.

Once configured, Home Assistant reads measurements **directly over Bluetooth**. The integration does not use the Jackery cloud API for periodic telemetry.

## Entities

### Electrical measurements

| Group | Entities |
| --- | --- |
| Power | Total power and phase 1–3 power |
| Voltage | Phase 1–3 voltage |
| Current | Total current and phase 1–3 current |
| Optional fields | General voltage, frequency, power factor, apparent power, reactive power, `enMask`, and secondary `l2*` measurements |

The integration scales P1 current values by **0.1** to convert them to amperes. Some units and signed-power conventions are still being verified.

Phase 2/3 entities are disabled by default during initial setup if those phases report zero voltage. Other optional entities may be registered but **disabled or unavailable** if the firmware does not transmit the corresponding value; missing measurements are not invented. Unknown measurement scaling is exposed as raw values.

### Diagnostics and Logbook

Available diagnostics include Bluetooth connection status, Bluetooth RSSI (when advertised), and the time of the last successful telemetry update.

**Bluetooth connected** and **Last successful update** are disabled by default for new installations, since frequent status/timestamp changes can clutter Home Assistant's Logbook. Existing entity-registry settings are preserved across upgrades.

To change their availability, open **Settings → Devices & services → Entities**. Alternatively, keep the entities enabled and exclude their actual entity IDs from Logbook:

```yaml
logbook:
  exclude:
    entities:
      - sensor.jackery_smart_meter_p1_last_successful_update
      - binary_sensor.jackery_smart_meter_p1_bluetooth_connected
```

Replace the sample IDs with your own. Logbook exclusions do not disable the sensors or control Recorder/history. Optional electrical measurements remain normal measurement entities, not diagnostic entities.

## Read-only Home Assistant actions

Under **Developer Tools → Actions**, the integration provides:

| Action | Purpose |
| --- | --- |
| `jackery_p1.read_wifi` | Scan nearby Wi-Fi networks |
| `jackery_p1.read_timezone` | Read meter time-zone information |
| `jackery_p1.read_device_info` | Read electrical telemetry |
| `jackery_p1.send_command` | Send a supported read-only BLE command |

All actions require the Home Assistant **configuration entry ID** (`entry_id`), **not** the P1 serial number or Bluetooth key.

Example: request a fresh measurement using the read-only command console:

```yaml
action: jackery_p1.send_command
data:
  entry_id: YOUR_HOME_ASSISTANT_CONFIG_ENTRY_ID
  command: 106
```

The command console permits only `1` (Wi-Fi scan), `22` (time zone) or `106` (device information). The actions share the integration's encrypted BLE transport and serialize access with regular polling. Responses redact potentially sensitive fields.

**Configuration writes and arbitrary/unknown commands are not supported.** In particular, Wi-Fi/MQTT provisioning and time-zone modification are deliberately not exposed.

## How it works

1. Home Assistant discovers and connects to the P1 using Bluetooth.
2. The integration authenticates its encrypted messages using the stored device-specific key.
3. Approximately every five seconds, it requests measurements and processes decrypted notifications.
4. Sensors update with the values actually returned; the integration reconnects if the BLE connection fails.

For protocol framing, encryption and command details, see the [BLE protocol research](docs/ble-protocol.md).

## Limitations

- **Power direction:** Import/export sign and the distinction between `power` and `power1` still require independent verification.
- **Energy totals:** The currently observed BLE measurement response does not include a cumulative energy counter.
- **Device-dependent fields:** Optional measurements may not be supplied by P1 firmware and will remain disabled or unavailable.
- **Transport:** This integration uses BLE; it does **not** currently consume MQTT telemetry or offer a local MQTT proxy.

## Reverse-engineering research

The repository also documents investigations into the P1's firmware, hardware and cloud communication. These are **research notes**, not installation requirements or supported integration features.

- [Reverse-engineering overview](docs/reverse-engineering.md) — ESP32-C3 hardware, UART logging, PCB tracing, TLS experiments and open questions.
- [BLE protocol](docs/ble-protocol.md) — GATT characteristics, encrypted framing, commands and measurements.
- [MQTT protocol](docs/mqtt-protocol.md) — observed topics, payloads, delta updates, reporting configuration and TLS limitations.

Findings distinguish confirmed observations from hypotheses; examples are sanitized to avoid exposing device-specific credentials.

## License

[MIT](LICENSE)
