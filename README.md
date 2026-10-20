# Jackery P1 Smart Meter for Home Assistant

[![GitHub release](https://img.shields.io/github/release/chill-uk/jackery-p1-ha?include_prereleases=&sort=semver&color=blue)](https://github.com/chill-uk/jackery-p1-ha/releases/)
[![Validation](https://github.com/chill-uk/jackery-p1-ha/actions/workflows/validate.yml/badge.svg)](https://github.com/chill-uk/jackery-p1-ha/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub issues](https://img.shields.io/github/issues/chill-uk/jackery-p1-ha)](https://github.com/chill-uk/jackery-p1-ha/issues)
[![GitHub downloads](https://img.shields.io/github/downloads/chill-uk/jackery-p1-ha/total)](https://github.com/chill-uk/jackery-p1-ha/releases/)

A **local LAN and Bluetooth integration** for the **Jackery Smart Meter P1 Reader (model 4001)**. It reads measurements directly into Home Assistant without ongoing Jackery cloud telemetry.

Bluetooth communication is encrypted; LAN HTTP access uses the meter's existing Wi-Fi setup. Only Bluetooth mode needs a device-specific key.

> [!IMPORTANT]
> This is an **unofficial community integration**, not affiliated with or supported by Jackery.
>
> The project is still under development. Import/export power sign conventions, cumulative energy counters and some optional measurement units are **not yet independently validated**. Do not use raw energy counters for billing or Home Assistant Energy Dashboard statistics without confirming their units and reset behaviour.

## Known meter limitations

The Jackery P1 does not currently provide every reading your smart meter might support. These are limitations of the information available from the Jackery device, not settings that can be enabled in Home Assistant.

- **Some electricity readings are missing.** The integration can show the values Jackery makes available, but not separate day/night tariff totals, energy totals for each phase, or the complete original message from your electricity meter. Home Assistant cannot recreate missing readings.
- **Gas readings are not available.** The Jackery P1 does not currently provide gas usage (or readings from other connected utility meters) through the local connections we support, so this integration cannot show gas consumption. We cannot rule out different behaviour in future firmware versions.

## Connection modes

| Mode | Setup | Normal operation |
| --- | --- | --- |
| **LAN (recommended)** | Connect the P1 to Wi-Fi with the official Jackery app. Enter its IP address or hostname in Home Assistant. | Local HTTP polling of `/device_info`, `/api/measurement` and `/api/monitor`; no Jackery credentials or BLE key required in Home Assistant. |
| **Bluetooth** | Retrieve the device-specific key through a one-time Jackery account login or enter an existing Base64 key. | Local encrypted BLE polling; no ongoing cloud connection required. |

Existing BLE entries continue to use Bluetooth automatically. For LAN mode the P1's local HTTP server must be reachable; availability over extended periods still needs device testing.

## Features

- **Local electrical measurements** over LAN HTTP or encrypted BLE; default polling interval **5 seconds**, configurable from 5–300 seconds.
- **Total and per-phase power, voltage and current** sensors, where supplied by the meter.
- **Optional additional measurements**, LAN monitoring metrics and Bluetooth diagnostics where applicable.
- **Read-only Home Assistant actions** for Wi-Fi scanning, time-zone information and meter readings.
- **No ongoing Jackery cloud dependency for telemetry** after the Bluetooth key has been obtained.
- **Independent LAN endpoint handling:** electrical readings can continue updating when the monitoring endpoint fails, and vice versa.
- **Reconfigure the connection** or move between LAN/BLE without deleting the Home Assistant configuration entry.

## Requirements

- A **Jackery Smart Meter P1 Reader (model 4001)**.
- For **LAN**, the P1 must already be connected to Wi-Fi and reachable via HTTP from Home Assistant. 
- For **Bluetooth**, Home Assistant needs a working Bluetooth adapter or an **active, connectable Bluetooth proxy** in range of the P1.
- For **Bluetooth only**, the device's **Base64-encoded AES key**, provided directly or retrieved during setup using a Jackery account with the P1 bound to it.

## Installation

### HACS (recommended)

[![Add to HACS via My Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=chill-uk&repository=jackery-p1-ha&category=integration)

1. Add this repository as a **custom integration** in [HACS](https://www.hacs.xyz/), using the button above or the repository URL.
2. Install **Jackery P1 (Local LAN / Bluetooth)**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**, then select **Jackery P1 (Local LAN / Bluetooth)**.
5. Follow the [configuration](#configuration) steps below.

> [!NOTE]
> The HACS distribution uses the `jackery_p1.zip` asset attached to a tagged GitHub release. If no compatible release asset is available, use [manual installation](#manual-installation).

### Manual installation

1. Download `jackery_p1.zip` from the [latest release](https://github.com/chill-uk/jackery-p1-ha/releases/latest), if available, **or** copy the [`custom_components/jackery_p1`](custom_components/jackery_p1) directory from this repository.
2. Place the integration files in `<config>/custom_components/jackery_p1/` in your Home Assistant configuration directory. If using the ZIP, its contents are the **integration files**, not a nested `jackery_p1` directory.
3. Restart Home Assistant.
4. Add **Jackery P1 (Local LAN / Bluetooth)** from **Settings → Devices & services**.

## Configuration

Choose **LAN (local HTTP)**, **Jackery account** or **Existing Bluetooth key** during setup:

| Setup method | When to use it |
| --- | --- |
| **LAN (local HTTP)** | P1 Wi-Fi is already configured in the Jackery app. Enter the meter's local hostname or IP address. |
| **Jackery account** | Your P1 is bound to your Jackery account and you want the integration to retrieve its Bluetooth key once. Provide your account credentials and two-letter region code (default: `NL`). |
| **Existing Bluetooth key** | You already have the device's Base64 AES key and want to configure the integration without account sign-in. |

The integration stores the device's **Bluetooth address and AES key**, but **does not store your Jackery password or account session token**. Treat the key as sensitive and never include it in public logs or issue reports.

Once configured, Home Assistant reads measurements **directly over the selected local transport** (LAN HTTP or encrypted Bluetooth). The integration does not use the Jackery cloud API for periodic telemetry.

### Changing the connection or polling interval

- **Settings → Devices & services → Jackery P1 → Configure:** set the polling interval (5–300 seconds). The integration reloads when it changes.
- **Settings → Devices & services → Jackery P1 → Reconfigure:** change LAN hostname/IP or switch transport between LAN and BLE. BLE requires an existing device-specific key; the account login is only offered during initial setup.

Reconfiguration keeps the same Home Assistant config entry and existing sensor unique IDs, preserving entity history. **Verify that the new connection belongs to the same physical P1.** A serial-number mismatch is rejected when the existing entry contains a known serial; older BLE entries do not necessarily contain one. Setting up a second copy of the device separately can still create duplicate entries.

## Entities

### Electrical measurements

| Group | Entities |
| --- | --- |
| Power | Total power and phase 1–3 power |
| Voltage | Phase 1–3 voltage |
| Current | Total current and phase 1–3 current |
| Optional fields | General voltage, frequency, power factor, apparent power, reactive power, `enMask`, and secondary `l2*` measurements |
| Optional derived power | Grid import/export power calculated from the sign of the reported `power` value; **disabled by default**, because the sign convention is not fully validated |

The integration scales P1 current values by **0.1** to convert them to amperes. Optional **Grid import power (assumed sign)** and **Grid export power (assumed sign)** use positive values as import and negative values as export; enable these entities only if that matches your meter's readings. They do not create additional OBIS measurements.

`engy` and `engyo` remain **raw optional fields**, not cumulative kWh sensors: their units, availability and reset behaviour must be validated before assigning `total_increasing` statistics. The integration does not invent separate tariff or phase energy totals that the device does not expose.

Phase 2/3 entities are disabled by default during initial setup if those phases report zero voltage. Other optional entities may be registered but **disabled or unavailable** if the firmware does not transmit the corresponding value; missing measurements are not invented. Unknown measurement scaling is exposed as raw values.

### Diagnostics and Logbook

Available diagnostics include Bluetooth connection status, Bluetooth RSSI (when advertised), and the time of the last successful telemetry update. LAN mode also provides independent measurement/monitor endpoint availability, their last successful update timestamps, response durations and consecutive failure counters. New diagnostics are disabled by default.

If one LAN endpoint fails, sensors reported only by that endpoint become unavailable while the other endpoint's sensors continue to update. If both endpoints fail, the coordinator reports an update failure. These diagnostics never include HTTP response bodies, Wi-Fi credentials or Bluetooth keys.

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

- **LAN mode:** After the official app has configured Wi-Fi, Home Assistant reads `/device_info` during setup and polls the meter's local HTTP measurement and monitor endpoints.
- **Bluetooth mode:** Home Assistant connects using a supported Bluetooth adapter or active proxy, encrypts read-only requests with the stored device-specific key, and processes notification responses.
- Both modes update sensors every five seconds by default, or at the configured interval. Neither requires cloud access for routine telemetry; only optional Bluetooth key retrieval during setup uses a Jackery account.

## Limitations

- **Power direction:** Import/export sign and the distinction between `power` and `power1` still require independent verification.
- **Energy totals:** The currently observed BLE measurement response does not include a confirmed cumulative energy counter. Optional raw `engy` and `engyo` fields must not be assumed to be high-resolution kWh counters or used directly in Home Assistant's Energy Dashboard.
- **Device-dependent fields:** Optional measurements may not be supplied by P1 firmware and will remain disabled or unavailable.
- **Transport:** The integration supports LAN HTTP and encrypted BLE; it does **not** currently consume MQTT telemetry or include an MQTT proxy.
- **Setup:** Wi-Fi must first be provisioned through the Jackery app. LAN monitoring subsequently works locally; Bluetooth still requires a device-specific key acquired beforehand.
- **Connection limitations:** The LAN API is unencrypted HTTP and should only be reachable on a trusted local network. The integration is read-only and does not provide Wi-Fi provisioning, firmware updates, MQTT configuration, factory-mode or UART controls.

## License

[MIT](LICENSE)
