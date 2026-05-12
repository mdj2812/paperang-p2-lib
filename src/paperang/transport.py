"""Paperang P2 — Transport layer abstraction.

Provides a pluggable physical transport interface so the same
protocol logic works over USB, Bluetooth, or any future medium.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Transport(ABC):
    """Abstract transport for Paperang P2 communication.

    Each transport provides raw byte-level send/recv.
    The protocol layer (packet framing, CRC, command codes)
    lives in :mod:`paperang.printer` and does not depend on
    the transport type.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the printer.

        Returns:
            True on success.
        Raises:
            RuntimeError if the printer is not found.
        """

    @abstractmethod
    def send(self, packet: bytes) -> None:
        """Send raw packet bytes to the printer."""

    @abstractmethod
    def recv(self, timeout: int = 1000) -> bytes:
        """Receive raw bytes from the printer.

        Args:
            timeout: Read timeout in milliseconds.

        Returns:
            Raw bytes received, or empty ``b''`` on timeout / error.
        """

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection and release resources."""


class UsbTransport(Transport):
    """USB transport for Paperang P2 (vendor-specific VID/PID)."""

    def __init__(self, vid: int = 0x4348, pid: int = 0x5584) -> None:
        """Initialize USB transport with vendor/product IDs.

        Args:
            vid: USB Vendor ID (default Paperang: 0x4348).
            pid: USB Product ID (default Paperang P2: 0x5584).
        """
        self.vid = vid
        self.pid = pid
        self._dev = None
        self._ep_out = None
        self._ep_in = None

    # ── Connection ──────────────────────────────────────────

    def connect(self) -> bool:
        """Find and claim the USB device."""
        import usb.core
        import usb.util

        self._dev = usb.core.find(idVendor=self.vid, idProduct=self.pid)
        if self._dev is None:
            raise RuntimeError("Paperang P2 printer not found")

        if self._dev.is_kernel_driver_active(0):
            self._dev.detach_kernel_driver(0)

        self._dev.set_configuration()
        cfg = self._dev.get_active_configuration()
        intf = cfg[(0, 0)]

        self._ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e:
                usb.util.endpoint_direction(e.bEndpointAddress)
                == usb.util.ENDPOINT_OUT,
        )
        self._ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e:
                usb.util.endpoint_direction(e.bEndpointAddress)
                == usb.util.ENDPOINT_IN,
        )
        return True

    # ── I/O ─────────────────────────────────────────────────

    def send(self, packet: bytes) -> None:
        """Write a raw packet to the USB OUT endpoint."""
        self._dev.write(self._ep_out.bEndpointAddress, packet)

    def recv(self, timeout: int = 1000) -> bytes:
        """Read from the USB IN endpoint.

        Returns empty bytes on any error (timeout, disconnect, etc.).
        """
        import usb.core  # for usb.core.USBError

        try:
            return self._dev.read(
                self._ep_in.bEndpointAddress, 64, timeout=timeout,
            )
        except usb.core.USBError:
            return b''

    def disconnect(self) -> None:
        """Release the USB device."""
        import usb.util

        if self._dev:
            try:
                usb.util.dispose_resources(self._dev)
            except Exception:
                pass
            self._dev = None
            self._ep_out = None
            self._ep_in = None
