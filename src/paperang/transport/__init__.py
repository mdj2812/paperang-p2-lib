"""Paperang P2 — Transport layer abstraction.

Provides a pluggable physical transport interface so the same
protocol logic works over USB, Bluetooth, or any future medium.
"""

from ._base import Transport
from ._bt import (  # noqa: F401
    BtTransport,
    PAPERANG_BT_NAMES,
    PAPERANG_SERVICE_UUID,
    check_paperang_uuid,
)
from ._usb import UsbTransport

__all__ = [
    "Transport",
    "UsbTransport",
    "BtTransport",
    "check_paperang_uuid",
    "PAPERANG_BT_NAMES",
    "PAPERANG_SERVICE_UUID",
]
