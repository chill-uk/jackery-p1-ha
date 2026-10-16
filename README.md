# Jackery P1 Smart Meter for Home Assistant

[![GitHub release](https://img.shields.io/github/release/chill-uk/jackery-p1-ha?include_prereleases=&sort=semver&color=blue)](https://github.com/chill-uk/jackery-p1-ha/releases/)
[![issues - jackery-p1-ha](https://img.shields.io/github/issues/chill-uk/jackery-p1-ha)](https://github.com/chill-uk/jackery-p1-ha/issues)
[![GH-code-size](https://img.shields.io/github/languages/code-size/chill-uk/jackery-p1-ha?color=red)](https://github.com/chill-uk/jackery-p1-ha)
[![GH-last-commit](https://img.shields.io/github/last-commit/chill-uk/jackery-p1-ha?style=flat-square)](https://github.com/chill-uk/jackery-p1-ha/commits/main)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validation](https://github.com/chill-uk/jackery-p1-ha/actions/workflows/validate.yml/badge.svg)](https://github.com/chill-uk/jackery-p1-ha/actions/workflows/validate.yml)
![GitHub Downloads](https://img.shields.io/github/downloads/chill-uk/jackery-p1-ha/total)

A local Bluetooth Home Assistant custom integration for the **Jackery Smart Meter P1 Reader** (model 4001). It reads encrypted BLE measurements directly from the meter using a device-specific key.

Telemetry polling **does not use the Jackery cloud API**. Optionally, a one-time Jackery account sign-in can retrieve the device's Bluetooth key during setup.

> [!IMPORTANT]
> This is an unofficial community integration. It is not affiliated with,
> endorsed by, connected with, or supported by Jackery.

> [!NOTE]
> The integration has been tested on a real P1. Interpretation of signed power and some optional measurement units is still being validated against independent DSMR readings. The extended shared accessory model does not guarantee that every field is transmitted by P1 firmware.

# Installation

### HACS installation

The quickest way to install this integration is via [HACS](https://github.com/hacs/integration) by clicking the button below:

[![Add to HACS via My Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=chill-uk&repository=jackery-p1-ha&category=integration)

1. Click the button above to add this repository to HACS as a custom integration.
2. Install **Jackery P1 (Local Bluetooth)** from HACS.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**.
5. Select **Jackery P1 (Local Bluetooth)**.
6. Choose **Jackery account** for one-time key retrieval or **Existing Bluetooth key** if you already have its Base64-encoded key.

HACS downloads the integration from the `jackery_p1.zip` asset of a tagged GitHub release. Until the first release is published, install manually or use a compatible development workflow.

### Manual installation

1. Download `jackery_p1.zip` from the [latest release](https://github.com/chill-uk/jackery-p1-ha/releases/latest), if available, and extract its contents into `<config>/custom_components/jackery_p1/`. The ZIP contents are the **integration files**, not an enclosing `jackery_p1` folder.
2. Alternatively, copy the repository's `custom_components/jackery_p1/` directory into `<config>/custom_components/jackery_p1/`.
3. Restart Home Assistant.
4. Add **Jackery P1 (Local Bluetooth)** from **Settings → Devices & services**.

## Bluetooth and authentication

The P1 must be reachable by a local Bluetooth adapter or an **active, connectable Bluetooth proxy**. During setup:

- **Jackery account:** Provide your account email, password and two-letter region code (default `NL`). The integration uses HTTPS to request the device's Base64 Bluetooth AES key from your bound P1. It stores only the BLE address and key, not your login password or session token.
- **Existing Bluetooth key:** Provide the Base64 AES key yourself. Keep it private; never include it in issue reports or public logs.

Once configured, electrical measurements are queried over local Bluetooth every five seconds.

## Sensors

- Total power, phase 1–3 power and phase 1–3 voltage.
- Total current and phase 1–3 current (P1 current values are scaled by `0.1` to amperes).
- Optional fields from the shared accessory model: general voltage, frequency, power factor, apparent power, reactive power, `enMask`, and secondary `l2*` measurements.
- Diagnostics: Bluetooth connected, Bluetooth signal strength (RSSI, when advertised), and last successful telemetry update.

Phase 2/3 readings are disabled by default on initial setup when the meter reports zero voltage on those phases. Optional fields are registered but **disabled/unavailable unless transmitted by the firmware**; no missing value is invented. Unknown unit scaling is deliberately exposed as raw values.

Existing sensor unique IDs remain unchanged when sensor names are updated; Home Assistant may preserve user-renamed entity names.

## Read-only Bluetooth actions

The integration exposes these response-capable Home Assistant actions under **Developer Tools → Actions**:

| Action | Function |
| --- | --- |
| `jackery_p1.read_wifi` | Scan Wi-Fi networks |
| `jackery_p1.read_timezone` | Read time-zone information |
| `jackery_p1.read_device_info` | Read electrical telemetry |

Each requires the Home Assistant **configuration entry ID**, not the meter's serial number or Bluetooth key:

```yaml
action: jackery_p1.read_wifi
data:
  entry_id: YOUR_HOME_ASSISTANT_CONFIG_ENTRY_ID
```

They use the same encrypted BLE transport and serialise access with normal polling. Credential-like response fields are redacted. No configuration-writing commands are exposed.

## How it works

1. Discover or connect to the meter via Home Assistant Bluetooth.
2. Decode the device-specific Base64 AES key.
3. Establish a BLE connection and subscribe to notifications.
4. Send the encrypted `READ_DEVICE_INFO` command (BLE message type 106) every five seconds.
5. Verify and decrypt notifications, reassemble JSON frames, and update sensors.
6. Reconnect if the BLE connection fails.

## Limitations

- Import/export sign and the distinction between `power` and `power1` require further verification.
- No cumulative energy counter has been observed in the P1's BLE response.
- Optional measurements may remain unavailable because the device firmware does not supply them.
- The ZIP release workflow runs when a matching `v*` tag is pushed; committing workflow files alone does not publish a release.

## License

MIT
