"""Paperang P2 — Classic Bluetooth (BR/EDR) SPP transport.

Uses RFCOMM sockets for byte-level communication.  Paperang P2
advertises SPP (UUID 00001101) and a custom service (0000fee7)
over classic Bluetooth, *not* BLE GATT.
"""

from __future__ import annotations

import socket
import subprocess
import time

from ._base import Transport

# Paperang P2 classic Bluetooth constants
PAPERANG_BT_NAMES = {"paperang", "miaomiaoji"}
PAPERANG_SERVICE_UUID = "0000fee7-0000-1000-8000-00805f9b34fb"
SPP_UUID = "00001101-0000-1000-8000-00805f9b34fb"


def _scan_devices(timeout: float = 8.0) -> list[tuple[str, str]]:
    """Scan for Paperang devices via bluetoothctl.

    Returns:
        List of (address, name) tuples.
    """
    try:
        proc = subprocess.run(
            ["timeout", str(int(timeout)), "bluetoothctl", "scan", "on"],
            capture_output=True, text=True, timeout=timeout + 5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    devices: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines() + proc.stderr.splitlines():
        # bluetoothctl output: "[NEW] Device XX:XX:XX:XX:XX:XX Paperang_P2"
        if "[NEW] Device" in line:
            parts = line.split("Device ", 1)[-1].strip().split(" ", 1)
            if len(parts) >= 2:
                addr, name = parts[0], parts[1]
                name_lower = name.lower()
                if any(name_lower.startswith(n) for n in PAPERANG_BT_NAMES):
                    devices.append((addr, name))
    return devices


def _find_rfcomm_channel(address: str) -> int:
    """Query SDP to find the RFCOMM channel for the Paperang service.

    Falls back to channel 1 if sdptool is unavailable.
    """
    try:
        proc = subprocess.run(
            ["sdptool", "browse", address],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1

    # Parse sdptool output for the Paperang service
    # Channel line looks like: "Channel: 1" or "Channel/Port: 1"
    in_paperang_section = False
    for line in proc.stdout.splitlines():
        if PAPERANG_SERVICE_UUID.lower() in line.lower():
            in_paperang_section = True
        if "0000fee7" in line.lower():
            in_paperang_section = True
        if in_paperang_section and ("Channel" in line or "channel" in line):
            try:
                return int(line.split(":", 1)[-1].strip())
            except ValueError:
                pass
        # Section ends at next service or blank
        if in_paperang_section and (
            "Service Name:" in line or "Service RecHandle:" in line
        ):
            if "Channel" not in line:
                in_paperang_section = False

    # Fallback: try common SPP channel
    return 1


class BtTransport(Transport):
    """Classic Bluetooth SPP (RFCOMM) transport for Paperang P2.

    Uses Linux ``AF_BLUETOOTH`` sockets — no extra Python dependencies.

    Args:
        address: Bluetooth MAC address (e.g. ``"00:15:83:EB:05:17"``).
            If not given, scans for nearby Paperang devices.
        channel: RFCOMM channel number.  Auto-detected via SDP if
            not specified.
        timeout: Connection timeout in seconds.
    """

    def __init__(
        self,
        address: str | None = None,
        channel: int | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.address = address
        self._channel = channel
        self.timeout = timeout
        self._sock: socket.socket | None = None

    # ── Transport interface ─────────────────────────────────

    def connect(self) -> bool:
        """Discover (if needed) and connect to the printer via RFCOMM.

        Returns:
            True on success.

        Raises:
            RuntimeError: Device not found or connection failed.
        """
        # Stage 1 — discover
        if not self.address:
            devices = _scan_devices()
            if not devices:
                raise RuntimeError("Paperang P2 not found (no BT devices)")
            self.address = devices[0][0]

        # Stage 2 — find RFCOMM channel
        channel = self._channel
        if channel is None:
            channel = _find_rfcomm_channel(self.address)

        # Stage 3 — connect
        self._sock = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM
        )
        self._sock.settimeout(self.timeout)
        try:
            self._sock.connect((self.address, channel))
        except OSError as exc:
            self._sock.close()
            self._sock = None
            raise RuntimeError(
                f"Failed to connect to {self.address} channel {channel}: {exc}"
            ) from exc
        return True

    def send(self, packet: bytes) -> None:
        """Write raw packet bytes over the RFCOMM socket."""
        if self._sock is None:
            raise RuntimeError("BtTransport: not connected")
        self._sock.sendall(packet)

    def recv(self, timeout: int = 1000) -> bytes:
        """Read bytes from the RFCOMM socket.

        Args:
            timeout: Read timeout in milliseconds.

        Returns:
            Raw bytes, or empty ``b''`` on timeout / error.
        """
        if self._sock is None:
            return b""
        try:
            self._sock.settimeout(timeout / 1000.0)
            return self._sock.recv(4096)
        except socket.timeout:
            return b""
        except OSError:
            return b""

    def disconnect(self) -> None:
        """Close the RFCOMM socket."""
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    # ── Convenience ─────────────────────────────────────────

    @staticmethod
    def scan() -> list[tuple[str, str]]:
        """Scan for nearby Paperang devices.

        Returns:
            List of ``(address, name)`` tuples.
        """
        return _scan_devices()
