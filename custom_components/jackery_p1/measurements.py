"""Pure measurement helpers (no Home Assistant dependencies)."""

from __future__ import annotations


def split_signed_power(value: object) -> tuple[float, float] | None:
    """Interpret positive as import and negative as export when explicitly enabled.

    This convention has not been independently verified for all P1 firmware.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return (max(float(value), 0.0), max(-float(value), 0.0))
