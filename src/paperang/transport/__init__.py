"""Paperang P2 — Transport layer abstraction.

Provides a pluggable physical transport interface so the same
protocol logic works over USB, Bluetooth, or any future medium.
"""

from ._base import Transport
from ._bt import BtTransport, PAPERANG_SERVICE_UUID, check_paperang_uuid  # noqa: F401
from ._usb import UsbTransport

__all__ = ["Transport", "UsbTransport", "BtTransport"]
