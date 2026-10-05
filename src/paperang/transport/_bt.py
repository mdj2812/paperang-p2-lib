"""Paperang — Classic Bluetooth (BR/EDR) SPP transport.

Uses RFCOMM sockets for byte-level communication.  Paperang printers advertise
the standard SPP profile (00001101) and usually a vendor service (0000fee7)
over classic Bluetooth, *not* BLE GATT.

Model-specific Bluetooth details (name prefixes, service UUIDs, an explicit
RFCOMM channel) come from :mod:`paperang.models`.  The module-level constants
below are the union across registered models and are kept for compatibility.

Discovery and channel lookup are deliberately model-agnostic: the model can
only be identified after the link is up (via ``CMD_GET_MODEL``), because
Bluetooth has no equivalent of USB VID/PID.
"""

from __future__ import annotations

import logging
import re
import socket
import subprocess

from ..models import bt_name_prefixes, bt_service_uuids, get_model
from ._base import Transport

log = logging.getLogger(__name__)

#: Standard Bluetooth Serial Port Profile, used as the primary probe.
SPP_UUID = "00001101-0000-1000-8000-00805f9b34fb"

#: Paperang vendor service UUID (P2).  Kept as the canonical value; see
#: :data:`PAPERANG_SERVICE_UUIDS` for every registered model.
PAPERANG_SERVICE_UUID = "0000fee7-0000-1000-8000-00805f9b34fb"

#: Name prefixes used for discovery, as a union across registered models.
#: The fallback keeps discovery working if a model file omits them.
PAPERANG_BT_NAMES = set(bt_name_prefixes()) or {"paperang", "miaomiaoji"}

#: Service UUIDs used for discovery, as a union across registered models.
PAPERANG_SERVICE_UUIDS = bt_service_uuids() or (PAPERANG_SERVICE_UUID,)


def check_paperang_uuid(address: str, service_uuids=None) -> bool:
    """Check if a Bluetooth device advertises the Paperang service UUID.

    Queries ``bluetoothctl info`` for the device's UUID list and returns
    True if any known Paperang service UUID is present.

    Args:
        address: Bluetooth MAC address.
        service_uuids: UUIDs to look for.  Defaults to every registered model.
    """
    wanted = tuple(u.lower() for u in (service_uuids or PAPERANG_SERVICE_UUIDS))
    try:
        info = subprocess.run(
            ["bluetoothctl", "info", address],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    stdout = info.stdout.lower()
    return any(uuid in stdout for uuid in wanted)


def _scan_devices(
    timeout: float = 8.0,
    name_prefixes=None,
    service_uuids=None,
) -> list[tuple[str, str]]:
    """Scan for Paperang devices via bluetoothctl.

    Args:
        timeout: Scan duration in seconds.
        name_prefixes: Device-name prefixes to accept.  Defaults to every
            registered model.
        service_uuids: Service UUIDs to accept.  Defaults to every registered
            model.

    Returns:
        List of (address, name) tuples.

    Discovery strategy:
    1. Collect ALL [NEW] Device entries (no filtering)
    2. Name starts with paperang/miaomiaoji → fast path accept
    3. Otherwise → bluetoothctl info <addr>, check for the known service UUIDs

    This ensures renamed devices and non-standard name variants are still
    discoverable by their SDP service UUID.
    """
    prefixes = tuple(name_prefixes) if name_prefixes else tuple(PAPERANG_BT_NAMES)
    try:
        proc = subprocess.run(
            ["bluetoothctl", "--timeout", str(int(timeout)), "scan", "on"],
            capture_output=True, text=True, timeout=timeout + 10,
        )
        output = proc.stdout + proc.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        output = ""

    # Phase 1: collect all device lines (don't filter yet).  `scan on` emits
    # "[NEW] Device …"; `bluetoothctl devices` (the fallback below) emits
    # "Device …".
    all_devices: list[tuple[str, str]] = []
    for line in output.splitlines():
        if "Device " in line:
            parts = line.split("Device ", 1)[-1].strip().split(" ", 1)
            if len(parts) >= 2:
                all_devices.append((parts[0], parts[1]))

    # Some BlueZ builds return immediately from `scan on` without printing
    # results.  Fall back to the devices BlueZ already knows about, which
    # covers already-paired printers.
    if not all_devices:
        try:
            known = subprocess.run(
                ["bluetoothctl", "devices"],
                capture_output=True, text=True, timeout=5,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []
        for line in (known.stdout + known.stderr).splitlines():
            if "Device " in line:
                parts = line.split("Device ", 1)[-1].strip().split(" ", 1)
                if len(parts) >= 2:
                    all_devices.append((parts[0], parts[1]))

    # Phase 2: accept by name (fast path) or UUID (fallback)
    devices: list[tuple[str, str]] = []
    for addr, name in all_devices:
        name_lower = name.lower()
        if any(name_lower.startswith(n) for n in prefixes):
            devices.append((addr, name))
            continue

        if check_paperang_uuid(addr, service_uuids):
            devices.append((addr, name))

    return devices


def _parse_sdp_records(output: str) -> list[tuple[int, str]]:
    """Parse ``sdptool browse`` output into (channel, record text) pairs.

    Records start at ``Service Name:``; a record is only returned when it
    carries a channel, since that is all the caller needs.
    """
    records: list[tuple[int, str]] = []
    lines: list[str] = []
    channel = None

    def flush():
        if channel is not None:
            records.append((channel, "\n".join(lines)))

    for line in output.splitlines():
        if line.strip().startswith("Service Name:"):
            flush()
            lines = []
            channel = None
        lines.append(line.lower())
        match = re.match(r"\s*channel(?:/port)?:\s*(\d+)", line.lower())
        if match:
            channel = int(match.group(1))

    flush()
    return records


def _find_rfcomm_channel(address: str, service_uuids=None, fallback: int = 1) -> int:
    """Query SDP to find the RFCOMM channel for the Paperang service.

    Probes the vendor service UUIDs first, which keeps established models on
    the channel they already used, then falls back to the standard SPP profile
    so that models advertising no vendor UUID still connect.  Returns
    ``fallback`` when nothing matches or sdptool is unavailable.
    """
    custom = tuple(u.lower() for u in (service_uuids or PAPERANG_SERVICE_UUIDS))
    try:
        proc = subprocess.run(
            ["sdptool", "browse", address],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return fallback

    records = _parse_sdp_records(proc.stdout)

    # 1. Vendor-specific service UUIDs (from the model table).  Checked first
    #    so printers that advertise both keep using the channel they used
    #    before this became model-agnostic.
    for channel, text in records:
        if any(uuid in text for uuid in custom):
            log.debug(
                "RFCOMM channel %d for %s from vendor UUID", channel, address
            )
            return channel

    # 2. Standard Serial Port Profile — present on any SPP printer, and the
    #    only signal on models that advertise no vendor UUID.
    for channel, text in records:
        if SPP_UUID in text or "0x1101" in text or "serial port" in text:
            log.debug("RFCOMM channel %d for %s from SPP", channel, address)
            return channel

    log.debug("No matching SDP service for %s; using channel %d", address, fallback)
    return fallback


class BtTransport(Transport):
    """Classic Bluetooth SPP (RFCOMM) transport for Paperang printers.

    Uses Linux ``AF_BLUETOOTH`` sockets — no extra Python dependencies.

    Args:
        address: Bluetooth MAC address (e.g. ``"00:15:83:EB:05:17"``).
            If not given, scans for nearby Paperang devices.
        channel: RFCOMM channel number.  Auto-detected via SDP if
            not specified.
        timeout: Connection timeout in seconds.
        model: Hardware model (a registered name or a
            :class:`~paperang.models.PrinterModel`).  When given, its
            Bluetooth name prefixes, service UUIDs and known channel are used
            instead of the union across all models.
    """

    def __init__(
        self,
        address: str | None = None,
        channel: int | None = None,
        timeout: float = 10.0,
        model=None,
    ) -> None:
        self.address = address
        self._channel = channel
        self.timeout = timeout
        self.printer_model = get_model(model) if model is not None else None
        self._sock: socket.socket | None = None

    @property
    def _name_prefixes(self) -> tuple:
        """Name prefixes to match during discovery."""
        if self.printer_model is not None and self.printer_model.bt_name_prefixes:
            return self.printer_model.bt_name_prefixes
        return tuple(PAPERANG_BT_NAMES)

    @property
    def _service_uuids(self) -> tuple:
        """Service UUIDs to match during discovery and channel lookup."""
        if self.printer_model is not None and self.printer_model.bt_service_uuids:
            return self.printer_model.bt_service_uuids
        return PAPERANG_SERVICE_UUIDS

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
            devices = _scan_devices(
                name_prefixes=self._name_prefixes,
                service_uuids=self._service_uuids,
            )
            if not devices:
                raise RuntimeError("Paperang printer not found (no BT devices)")
            self.address = devices[0][0]

        # Stage 2 — find RFCOMM channel
        channel = self._channel
        if channel is None and self.printer_model is not None:
            channel = self.printer_model.bt_rfcomm_channel
        if channel is None:
            channel = _find_rfcomm_channel(self.address, self._service_uuids)

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

        Restores the socket timeout after reading so that subsequent
        ``send()`` calls (e.g. print_bitmap) use the full connection
        timeout instead of the shorter read timeout.
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
        finally:
            self._sock.settimeout(self.timeout)

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
