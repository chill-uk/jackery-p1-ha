"""Offline LAN regressions without requiring a Home Assistant installation."""

import ast
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pytest


class FakeCoordinator:
    def __class_getitem__(cls, _item):
        return cls

    def __init__(self, hass, logger, name, update_interval):
        self.hass = hass
        self.update_interval = update_interval
        self.last_update_success = True


class UpdateFailed(Exception):
    pass


def _load_lan():
    """Compile the production LAN functions with lightweight dependency stubs."""
    source = Path(__file__).resolve().parents[1] / "custom_components/jackery_p1/lan.py"
    tree = ast.parse(source.read_text())
    selected = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    namespace = {
        "__name__": "offline_lan_test",
        "__annotations__": {},
        "HomeAssistant": object,
        "DataUpdateCoordinator": FakeCoordinator,
        "UpdateFailed": UpdateFailed,
        "ClientError": IOError,
        "TimeoutError": TimeoutError,
        "timedelta": timedelta,
        "datetime": datetime,
        "timezone": timezone,
        "urlsplit": urlsplit,
        "DOMAIN": "jackery_p1",
        "POLL_SECONDS": 5,
        "_LOGGER": None,
        "time": __import__("time"),
    }
    class Logger:
        def debug(self, *args):
            pass
    namespace["_LOGGER"] = Logger()
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), "exec"), namespace)
    return namespace


@pytest.mark.parametrize("bad", ["", "https://meter", "http://user:pass@meter", "http://meter/api/measurement", "http://meter?x=1"])
def test_invalid_lan_hosts_rejected(bad):
    with pytest.raises(ValueError):
        _load_lan()["normalize_host"](bad)


def test_independent_endpoint_failure_keeps_measurements():
    ns = _load_lan()
    async def read_json(_hass, _host, path):
        if path == "/device_info":
            return {"type": 4001, "sn": "EXAMPLE0001"}
        if path == "/api/measurement":
            return {"power": -125, "volt1": 230}
        raise TimeoutError()
    ns["read_json"] = read_json
    coordinator = ns["JackeryP1LanCoordinator"](object(), "meter.local", 15)
    result = asyncio.run(coordinator._async_update_data())
    assert result == {"power": -125, "volt1": 230}
    assert coordinator.update_interval == timedelta(seconds=15)
    assert coordinator.measurement_ok and not coordinator.monitor_ok
    assert coordinator.monitor_failures == 1
    assert coordinator.last_measurement_success is not None
    assert coordinator.last_monitor_success is None


def test_monitor_remains_when_measurement_fails():
    ns = _load_lan()
    async def read_json(_hass, _host, path):
        if path == "/device_info":
            return {"type": 4001, "sn": "EXAMPLE0001"}
        if path == "/api/measurement":
            raise TimeoutError()
        return {"uptime_s": 125}
    ns["read_json"] = read_json
    coordinator = ns["JackeryP1LanCoordinator"](object(), "meter.local")
    result = asyncio.run(coordinator._async_update_data())
    assert result == {"uptime_s": 125}
    assert coordinator.monitor_ok and not coordinator.measurement_ok


def test_both_endpoints_failed_raises():
    ns = _load_lan()
    async def read_json(_hass, _host, path):
        if path == "/device_info":
            return {"type": 4001, "sn": "EXAMPLE0001"}
        raise TimeoutError()
    ns["read_json"] = read_json
    coordinator = ns["JackeryP1LanCoordinator"](object(), "meter.local")
    with pytest.raises(UpdateFailed):
        asyncio.run(coordinator._async_update_data())
    assert coordinator.measurement_failures == coordinator.monitor_failures == 1
