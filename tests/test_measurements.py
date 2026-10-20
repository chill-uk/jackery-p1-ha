"""Derived power must never invent energy counters or misinterpret non-numbers."""

import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    "jackery_measurements", Path(__file__).resolve().parents[1] / "custom_components/jackery_p1/measurements.py"
)
measurement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measurement)


@pytest.mark.parametrize("input_value,expected", [
    (250, (250.0, 0.0)), (-125, (0.0, 125.0)), (0, (0.0, 0.0)),
    (None, None), ("123", None), (True, None),
])
def test_signed_power(input_value, expected):
    assert measurement.split_signed_power(input_value) == expected
