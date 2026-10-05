"""Paperang — USB transport implementation."""

from __future__ import annotations

from ..models import get_model
from ._base import Transport


class UsbTransport(Transport):
    """USB transport for Paperang printers (vendor-specific VID/PID)."""

    def __init__(
        self,
        vid: int | None = None,
        pid: int | None = None,
        pids=None,
        write_retries: int = 3,
        write_retry_delay: float = 0.5,
    ) -> None:
        """Initialize USB transport with vendor/product IDs.

        Args:
            vid: USB Vendor ID.  Defaults to the default model's VID
                (Paperang: 0x4348).
            pid: USB Product ID.  Defaults to the default model's PID
                (Paperang P2: 0x5584).
            pids: Several product IDs to try, in order.  Used when the model is
                not known yet; :attr:`matched_pid` reports which one answered.
                Takes precedence over ``pid``.
            write_retries: How many times a timed-out write is attempted before
                giving up.  ``1`` disables retrying.
            write_retry_delay: Seconds to wait before the second attempt; the
                wait grows linearly with each retry.
        """
        default_model = get_model()
        if vid is None:
            vid = default_model.vid
        if pids is None:
            pids = (default_model.pid if pid is None else pid,)
        self.vid = vid
        self.pids = tuple(pids)
        self.pid = self.pids[0]
        self.write_retries = max(1, int(write_retries))
        self.write_retry_delay = float(write_retry_delay)
        self.matched_pid = None
        self._dev = None
        self._ep_out = None
        self._ep_in = None

    # ── Connection ──────────────────────────────────────────

    def connect(self) -> bool:
        """Find and claim the USB device."""
        import usb.core
        import usb.util

        self._dev = None
        self.matched_pid = None
        for pid in self.pids:
            self._dev = usb.core.find(idVendor=self.vid, idProduct=pid)
            if self._dev is not None:
                self.matched_pid = pid
                break

        if self._dev is None:
            wanted = "/".join(f"0x{pid:04x}" for pid in self.pids)
            raise RuntimeError(
                f"Paperang printer not found (VID=0x{self.vid:04x}, PID={wanted})"
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
        """Write a raw packet to the USB OUT endpoint.

        A timed-out write is retried: the printer can be busy (feeding paper
        after a print, for example) and refuses new data until it is ready.  A
        single timeout would otherwise abort the whole job, which is what made
        consecutive print calls fail while the same calls worked one at a time.
        Other USB errors are raised immediately.
        """
        import time

        import usb.core  # for usb.core.USBError

        for attempt in range(self.write_retries):
            try:
                self._dev.write(self._ep_out.bEndpointAddress, packet)
                return
            except usb.core.USBError as exc:
                last_attempt = attempt == self.write_retries - 1
                if "timed out" not in str(exc).lower() or last_attempt:
                    raise
                time.sleep(self.write_retry_delay * (attempt + 1))

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
