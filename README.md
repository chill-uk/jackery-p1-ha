# Jackery P1 — local Bluetooth for Home Assistant

Early v0.1.0 integration for the Jackery Smart Meter P1 Reader (model 4001).  
Uses encrypted BLEs, validated against physical P1 hardware.  
No cloud requests during polling.

## Installation
Copy `custom_components/jackery_p1` to your HA `config/custom_components/` folder, restart, and add "Jackery P1 (Local Bluetooth)" from Devices & services.  

Enter the Base64 BLE key previously retrieved for your own device. Keep it private.  
OR user your Jackery login details.  

## Sensors
Total and per-phase raw signed active power (W), phase voltage (V), total and phase current (raw divided by 10 A).

## Limitations
Requires BLE range or a connectable Bluetooth proxy.  
The sign of power and relationship between total and phase power need DSMR verification.  
No cumulative energy readings are available.  

## One-time Jackery account key retrieval

During configuration, choose **Jackery account**, enter the email, password and two-letter region code (default `NL`).  
The integration sends the encrypted login payload to Jackery over HTTPS and looks up your bound P1.  

Your password and API token are not saved in the Home Assistant config entry;  
only the device-specific Base64 Bluetooth key and BLE address are stored.  

Normal telemetry polling is over local Bluetooth, without further cloud requests.

Alternatively, choose **Existing Bluetooth key** and enter it manually. (script coming later)

If the integration has already been configured, remove and re-add it to select a different setup method.

## Additional telemetry fields

The integration now recognises the extended accessory data model: general voltage, frequency, power factor, apparent and reactive power (including phase variants), `enMask`, and the `l2*` secondary channel fields. **Optional sensors are created only when a field appears in the initial device response.** Fields not transmitted by the P1 are not fabricated. Optional values are labelled `(raw)` because their units/scaling have not been confirmed on P1 hardware. Restart or reload the integration after a firmware change if it begins reporting new fields. The shared model is not evidence that every P1 firmware emits those values.

## Read-only BLE actions

Home Assistant exposes the response-capable actions `jackery_p1.read_wifi`, `jackery_p1.read_timezone`, and `jackery_p1.read_device_info`. These use the same BLE connection and key as the polling coordinator, and polling and manual reads are serialized. Each action requires the Home Assistant integration configuration `entry_id` (not the P1 MAC address):

```yaml
action: jackery_p1.read_wifi
data:
  entry_id: YOUR_HOME_ASSISTANT_CONFIG_ENTRY_ID
```

In **Developer Tools → Actions**, select the action and inspect its response. Wi-Fi and other credential-like fields are redacted in service responses. A time-out may mean the P1 firmware does not implement that particular command; it does not mean the device is disconnected. No BLE configuration write actions are exposed. The actions have not yet been tested against the actual P1 through Home Assistant.

## v0.2.0 sensor improvements

- Renamed existing power sensors to **Total power** and **Phase N power** (unique IDs unchanged). Import/export sign has **not** yet been validated against DSMR.
- Phase 2 and 3 entities are **disabled by default on first registration** when the first response indicates zero phase voltage. Existing entity-registry preferences are not overwritten; enable manually under the integration's entities if needed.
- All extended fields in the decompiled accessory model are registered. If a field is missing from the firmware response, it is **disabled by default** and reports unavailable if enabled. A future firmware response can populate the sensor once enabled. Units for unverified fields remain raw.
- Diagnostic entities: **Bluetooth signal strength** (RSSI from HA Bluetooth advertisements, may be unavailable when no advertisements are available), **Last successful update** (UTC timestamp of the latest successful telemetry query), and **Bluetooth connected** (whether the persistent client is currently connected).

Note: Bluetooth connected is a transport-state diagnostic, not proof the P1 is publishing new measurements. Existing renamed entities may retain user-customized names. Restart Home Assistant after updating; this version is not yet runtime-tested on your HA instance.
