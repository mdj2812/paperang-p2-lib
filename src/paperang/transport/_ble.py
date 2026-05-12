"""Paperang P2 — BLE (Bluetooth Low Energy) transport implementation.

Uses bleak for cross-platform BLE support.  Communication follows the
same packet protocol as USB: Paperang frames are written to a TX
characteristic and responses are received via RX characteristic
notifications.
"""

from __future__ import annotations

import asyncio

from ..constants import VENDOR_ID
from ._base import Transport

# Nordic UART Service — used by many BLE peripherals including Paperang P2
NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_TX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"       # write (phone→printer)
NUS_RX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"       # notify (printer→phone)


class BleTransport(Transport):
    """BLE transport for Paperang P2.

    Uses the Nordic UART Service (NUS) for byte-level communication.

    Args:
        address: BLE MAC address of the printer. If not provided,
            ``name`` is used for scanning.
        name: Device name prefix to scan for.  Default ``"Paperang"``.
        service_uuid: Override the UART service UUID.
        tx_uuid: Override the TX (write) characteristic UUID.
        rx_uuid: Override the RX (notify) characteristic UUID.
        timeout: Connection timeout in seconds.
    """

    def __init__(
        self,
        address: str | None = None,
        name: str = "Paperang",
        service_uuid: str = NUS_SERVICE_UUID,
        tx_uuid: str = NUS_TX_UUID,
        rx_uuid: str = NUS_RX_UUID,
        timeout: float = 15.0,
    ) -> None:
        self.address = address
        self.name = name
        self.service_uuid = service_uuid
        self.tx_uuid = tx_uuid
        self.rx_uuid = rx_uuid
        self.timeout = timeout

        self._client = None
        self._tx_char = None
        self._rx_buffer: bytearray = bytearray()

    # ── Transport interface ─────────────────────────────────

    def connect(self) -> bool:
        """Discover and connect to the printer via BLE.

        Blocks until connected or timeout.
        """
        return asyncio.get_event_loop().run_until_complete(
            self._async_connect()
        )

    def send(self, packet: bytes) -> None:
        """Write a raw packet to the TX characteristic."""
        asyncio.get_event_loop().run_until_complete(
            self._client.write_gatt_char(self.tx_uuid, packet, response=False)
        )

    def recv(self, timeout: int = 1000) -> bytes:
        """Read accumulated bytes from the RX buffer.

        Blocks up to ``timeout`` ms waiting for data.  Returns all
        buffered bytes, or empty ``b''`` on timeout.
        """
        # We use a simple polling loop; for production a proper async
        # mechanism (asyncio.Queue) would be better, but the protocol
        # layer calls recv() in a blocking executor already.
        deadline = asyncio.get_event_loop().time() + timeout / 1000.0
        while not self._rx_buffer:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                return b""
            asyncio.get_event_loop().run_until_complete(
                asyncio.sleep(min(remaining, 0.05))
            )
        data = bytes(self._rx_buffer)
        self._rx_buffer.clear()
        return data

    def disconnect(self) -> None:
        """Disconnect from the printer."""
        if self._client and self._client.is_connected:
            asyncio.get_event_loop().run_until_complete(
                self._client.disconnect()
            )
        self._client = None
        self._tx_char = None
        self._rx_buffer.clear()

    # ── BLE internals ───────────────────────────────────────

    async def _async_connect(self) -> bool:
        """Async BLE connection flow."""
        from bleak import BleakScanner, BleakClient

        # Stage 1 — discover device
        if self.address:
            device = None
            # Quick scan to verify the device is present
            devices = await BleakScanner.discover(timeout=5)
            for d in devices:
                if d.address.lower() == self.address.lower():
                    device = d
                    break
            if device is None:
                raise RuntimeError(
                    f"Paperang P2 not found at {self.address}"
                )
        else:
            # Scan by name prefix
            device = await BleakScanner.find_device_by_filter(
                lambda d, ad: bool(
                    d.name and d.name.lower().startswith(self.name.lower())
                ),
                timeout=10,
            )
            if device is None:
                raise RuntimeError(
                    f"Paperang P2 not found (name prefix: {self.name})"
                )

        # Stage 2 — connect
        self._client = BleakClient(
            device, timeout=self.timeout, disconnected_callback=self._on_disconnect
        )
        await self._client.connect()

        # Stage 3 — discover characteristics
        await self._client.start_notify(
            self.rx_uuid, self._on_rx_notification
        )

        return True

    def _on_rx_notification(self, sender: int, data: bytearray) -> None:
        """Callback for RX characteristic notifications."""
        self._rx_buffer.extend(data)

    def _on_disconnect(self, client) -> None:
        """Callback for unexpected disconnections."""
        self._client = None
