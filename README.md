# Jackery P1 — local Bluetooth for Home Assistant

Early v0.1.0 integration for the Jackery Smart Meter P1 Reader (model 4001). Uses encrypted BLE command 106, validated against physical P1 hardware. No cloud requests during polling.

## Installation
Copy `custom_components/jackery_p1` to your HA `config/custom_components/` folder, restart, and add "Jackery P1 (Local Bluetooth)" from Devices & services. Enter the Base64 BLE key previously retrieved for your own device. Keep it private; never commit `.jackery-key`.

## Sensors
Total and per-phase raw signed active power (W), phase voltage (V), total and phase current (raw divided by 10 A).

## Limitations
Requires BLE range or a connectable Bluetooth proxy. The sign of power and relationship between total and phase power need DSMR verification. No cumulative energy readings are available. This first integration release has not yet been validated inside a running Home Assistant instance.
