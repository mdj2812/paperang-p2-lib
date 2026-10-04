"""Paperang — USB transport implementation."""

from __future__ import annotations

from ..models import get_model
from ._base import Transport


class UsbTransport(Transport):
    """USB transport for Paperang printers (vendor-specific VID/PID)."""

    def __init__(self, vid: int | None = None, pid: int | None = None) -> None:
        """Initialize USB transport with vendor/product IDs.

        Args:
            vid: USB Vendor ID.  Defaults to the default model's VID
                (Paperang: 0x4348).
            pid: USB Product ID.  Defaults to the default model's PID
                (Paperang P2: 0x5584).
        """
        if vid is None or pid is None:
            default_model = get_model()
            vid = default_model.vid if vid is None else vid
            pid = default_model.pid if pid is None else pid
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
            raise RuntimeError(
                f"Paperang printer not found (VID=0x{self.vid:04x}, "
                f"PID=0x{self.pid:04x})"
            )

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
