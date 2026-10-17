# Jackery P1 BLE protocol (research)

> Unofficial, partially reverse-engineered protocol. See [overview](reverse-engineering.md). This reference describes observed behaviour rather than a complete specification.

## GATT transport

| Role | UUID |
|---|---|
| Service | `0000bdee-0000-1000-8000-00805f9b34fb` |
| Write | `0000ee01-0000-1000-8000-00805f9b34fb` |
| Notify | `0000ee02-0000-1000-8000-00805f9b34fb` |

**Confirmed:** Custom `0xDFED` message framing, fragmentation, CRC16 and AES-CBC encryption with PKCS7 padding and a per-device AES key. Consult `custom_components/jackery_p1/protocol.py` for the byte-level implementation. Never publish device keys.

## Known command IDs

| ID | Observation |
|---|---|
| 1 | Wi-Fi scan; network names and RSSI in response |
| 2 | Set Wi-Fi credentials and MQTT host/port (write; **not exposed in HA**) |
| 3 | Set time/timezone (write; observed from official app) |
| 22 | Read timezone (implemented in integration) |
| 106 | Retrieve instantaneous electrical data |
| 107 | Unsolicited voltage/current notification observed during BLE session |

Example **sanitized** command 106 response:

```json
{"cmd":106,"volt1":237,"volt2":0,"volt3":0,"curr1":40,"curr2":0,"curr3":0,"curr":40,"power1":221,"power2":0,"power3":0,"power":223}
```

The integration currently scales current values by 0.1 to amperes. Power sign conventions and some optional measurement units require independent validation. The app sometimes receives partial unsolicited `cmd:107` updates.

## Integration and open questions

Home Assistant polls `cmd:106` every five seconds. Its public read-only actions support only `1`, `22` and `106`. No generic write-command console is exposed.

Unresolved: whether unsolicited updates can reliably replace polling, accurate import/export semantics, firmware-dependent field availability, and whether BLE advertising reveals provisioning/bound state. Observed advertising did not differentiate tested states.
