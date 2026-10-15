# Jackery P1 — local Bluetooth for Home Assistant

Early v0.1.0 integration for the Jackery Smart Meter P1 Reader (model 4001). Uses encrypted BLE command 106, validated against physical P1 hardware. No cloud requests during polling.

## Installation
Copy `custom_components/jackery_p1` to your HA `config/custom_components/` folder, restart, and add "Jackery P1 (Local Bluetooth)" from Devices & services. Enter the Base64 BLE key previously retrieved for your own device. Keep it private; never commit `.jackery-key`.

## Sensors
Total and per-phase raw signed active power (W), phase voltage (V), total and phase current (raw divided by 10 A).

## Limitations
Requires BLE range or a connectable Bluetooth proxy. The sign of power and relationship between total and phase power need DSMR verification. No cumulative energy readings are available. This first integration release has not yet been validated inside a running Home Assistant instance.

## One-time Jackery account key retrieval

During configuration, choose **Jackery account**, enter the email, password and two-letter region code (default `NL`). The integration sends the encrypted login payload to Jackery over HTTPS and looks up your bound P1 (model 4001). Your password and API token are not saved in the Home Assistant config entry; only the device-specific Base64 Bluetooth key and BLE address are stored. Normal telemetry polling is over local Bluetooth, without further cloud requests.

Alternatively, choose **Existing Bluetooth key** and enter it manually. For manual setup, you need the BLE address from Home Assistant's Bluetooth integration; macOS CoreBluetooth identifiers are not portable to Home Assistant.

If the integration has already been configured, remove and re-add it to select a different setup method. Login has only been tested via the standalone Mac utility, not yet through Home Assistant.
