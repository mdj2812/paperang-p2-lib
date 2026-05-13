"""Paperang P2 — Transport layer abstraction.

Provides a pluggable physical transport interface so the same
protocol logic works over USB, Bluetooth, or any future medium.
"""

from ._base import Transport
from ._ble import BleTransport
from ._usb import UsbTransport

__all__ = ["Transport", "UsbTransport", "BleTransport"]
