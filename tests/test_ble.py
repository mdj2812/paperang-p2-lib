"""Tests for paperang.transport._ble — constructor, Transport methods, callbacks.

Uses ``sys.modules`` mock so tests run without the optional ``[ble]``
dependency (bleak) installed.
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from paperang.transport._ble import BleTransport
from paperang.transport import Transport
from paperang.constants import NUS_SERVICE_UUID, NUS_TX_UUID, NUS_RX_UUID


# ── Fake bleak objects (stand-ins when bleak not installed) ──────────

class FakeBleakDevice:
    def __init__(self, address="AA:BB:CC:DD:EE:FF", name="Paperang P2S"):
        self.address = address
        self.name = name


class FakeBleakClient:
    def __init__(self, device, timeout=None, disconnected_callback=None):
        self.device = device
        self.is_connected = True
        self._disconnected_callback = disconnected_callback
        self.write_gatt_char = MagicMock()
        self.start_notify = AsyncMock()
        self.connect = AsyncMock()
        self.disconnect = AsyncMock()


class _FakeBleakScanner:
    """Mutable holder so tests can set discover / find_device_by_filter."""

    discover: object = AsyncMock(return_value=[])
    find_device_by_filter: object = AsyncMock(return_value=None)


def _make_fake_bleak_module():
    """Return an object that behaves like ``import bleak``."""
    class Mod:
        BleakScanner = _FakeBleakScanner
        BleakClient = FakeBleakClient
    return Mod


# ── Constructor ──────────────────────────────────────────────────────

class TestBleTransportInit:
    def test_defaults(self):
        t = BleTransport()
        assert t.name == "Paperang"
        assert t.address is None
        assert t.service_uuid == NUS_SERVICE_UUID
        assert t.tx_uuid == NUS_TX_UUID
        assert t.rx_uuid == NUS_RX_UUID
        assert t.timeout == 15.0
        assert t._client is None
        assert t._tx_char is None
        assert t._rx_buffer == bytearray()

    def test_custom_address(self):
        t = BleTransport(address="AA:BB:CC:DD:EE:FF")
        assert t.address == "AA:BB:CC:DD:EE:FF"

    def test_custom_name(self):
        t = BleTransport(name="P2")
        assert t.name == "P2"

    def test_custom_uuids(self):
        t = BleTransport(
            service_uuid="00001111-0000-0000-0000-000000000000",
            tx_uuid="00002222-0000-0000-0000-000000000000",
            rx_uuid="00003333-0000-0000-0000-000000000000",
        )
        assert t.service_uuid == "00001111-0000-0000-0000-000000000000"
        assert t.tx_uuid == "00002222-0000-0000-0000-000000000000"
        assert t.rx_uuid == "00003333-0000-0000-0000-000000000000"

    def test_custom_timeout(self):
        t = BleTransport(timeout=30.0)
        assert t.timeout == 30.0

    def test_is_transport(self):
        t = BleTransport()
        assert isinstance(t, Transport)


# ── Callbacks ────────────────────────────────────────────────────────

class TestBleCallbacks:
    def test_on_rx_notification(self):
        t = BleTransport()
        t._on_rx_notification(0, bytearray(b"\x02\x03"))
        t._on_rx_notification(0, bytearray(b"\xff"))
        assert t._rx_buffer == bytearray(b"\x02\x03\xff")

    def test_on_disconnect(self):
        t = BleTransport()
        t._client = object()
        t._on_disconnect(t._client)
        assert t._client is None


# ── recv ─────────────────────────────────────────────────────────────

class TestBleRecv:
    def test_returns_buffered_data_immediately(self):
        t = BleTransport()
        t._rx_buffer = bytearray(b"response")
        result = t.recv(timeout=1000)
        assert result == b"response"
        assert t._rx_buffer == bytearray()

    def test_timeout_returns_empty(self):
        t = BleTransport()
        loop = MagicMock()
        call_count = [0]

        def fake_time():
            call_count[0] += 1
            return call_count[0] * 2.0

        loop.time = fake_time
        loop.run_until_complete = MagicMock()

        with patch("asyncio.get_event_loop", return_value=loop):
            result = t.recv(timeout=100)

        assert result == b""


# ── disconnect ──────────────────────────────────────────────────────

class TestBleDisconnect:
    def test_no_client(self):
        t = BleTransport()
        t.disconnect()
        assert t._client is None

    def test_with_connected_client(self):
        t = BleTransport()
        t._client = FakeBleakClient(FakeBleakDevice())
        with patch("asyncio.get_event_loop") as mock_loop:
            t.disconnect()
        assert t._client is None
        assert t._tx_char is None

    def test_rx_buffer_cleared(self):
        t = BleTransport()
        t._rx_buffer.extend(b"hello")
        t.disconnect()
        assert t._rx_buffer == bytearray()


# ── send ─────────────────────────────────────────────────────────────

class TestBleSend:
    def test_sends_packet(self):
        t = BleTransport()
        t.tx_uuid = NUS_TX_UUID
        t._client = FakeBleakClient(FakeBleakDevice())
        with patch("asyncio.get_event_loop") as mock_loop:
            t.send(b"\x02\x04\x00\x01\x00\x01\x12\x34\x03")
        t._client.write_gatt_char.assert_called_once_with(
            NUS_TX_UUID, b"\x02\x04\x00\x01\x00\x01\x12\x34\x03", response=False
        )


# ── Helpers for async tests ──────────────────────────────────────────

def _run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def _fake_bleak_module(Scanner=None):
    """Build a fake bleak module.  Scanner replaces _FakeBleakScanner
    in BleakScanner so tests can set discover / find_device_by_filter."""
    class ScannerWrap:
        pass
    if Scanner is not None:
        for attr in ("discover", "find_device_by_filter"):
            if hasattr(Scanner, attr):
                setattr(ScannerWrap, attr, getattr(Scanner, attr))
    else:
        ScannerWrap.discover = AsyncMock(return_value=[])
        ScannerWrap.find_device_by_filter = AsyncMock(return_value=None)

    class Mod:
        BleakScanner = ScannerWrap
        BleakClient = FakeBleakClient
    return Mod


# ── _async_connect ──────────────────────────────────────────────────

class TestBleAsyncConnect:
    def test_connect_by_address_success(self):
        t = BleTransport(address="AA:BB:CC:DD:EE:FF")
        fake_dev = FakeBleakDevice()

        class Scanner:
            discover = AsyncMock(return_value=[fake_dev])

        with patch.dict(sys.modules, bleak=_fake_bleak_module(Scanner)):
            result = _run(t._async_connect())
            assert result is True
            assert t._client is not None

    def test_connect_by_address_not_found(self):
        t = BleTransport(address="AA:BB:CC:DD:EE:FF")

        class Scanner:
            discover = AsyncMock(return_value=[])

        with patch.dict(sys.modules, bleak=_fake_bleak_module(Scanner)):
            with pytest.raises(RuntimeError, match="not found at"):
                _run(t._async_connect())

    def test_connect_by_name_success(self):
        t = BleTransport()

        async def fake_find(filter_fn, timeout):
            # Verify filter: "Paperang" and "MiaoMiaoJi" are accepted
            class AD:
                pass
            ad = AD()
            assert filter_fn(FakeBleakDevice("AA:00", "Paperang P2S"), ad) is True
            assert filter_fn(FakeBleakDevice("AA:01", "MiaoMiaoJi-123"), ad) is True
            assert filter_fn(FakeBleakDevice("AA:01", "miaomiaoji-lite"), ad) is True
            assert filter_fn(FakeBleakDevice("AA:02", "SomeDevice"), ad) is False
            assert filter_fn(FakeBleakDevice("AA:03", None), ad) is False
            return FakeBleakDevice("AA:00", "Paperang P2S")

        class Scanner:
            find_device_by_filter = fake_find

        with patch.dict(sys.modules, bleak=_fake_bleak_module(Scanner)):
            result = _run(t._async_connect())
            assert result is True

    def test_connect_by_name_not_found(self):
        t = BleTransport()

        async def fake_find(filter_fn, timeout):
            return None

        class Scanner:
            find_device_by_filter = fake_find

        with patch.dict(sys.modules, bleak=_fake_bleak_module(Scanner)):
            with pytest.raises(RuntimeError, match="not found"):
                _run(t._async_connect())

    def test_connect_calls_start_notify(self):
        t = BleTransport(address="AA:BB:CC:DD:EE:FF")

        class Scanner:
            discover = AsyncMock(return_value=[FakeBleakDevice()])

        with patch.dict(sys.modules, bleak=_fake_bleak_module(Scanner)):
            _run(t._async_connect())
            t._client.start_notify.assert_called_once()
            args, _ = t._client.start_notify.call_args
            assert args[0] == NUS_RX_UUID


# ── connect (blocking wrapper) ──────────────────────────────────────

class TestBleConnect:
    def test_connect_returns_true(self):
        t = BleTransport(address="AA:BB:CC:DD:EE:FF")

        class Scanner:
            discover = AsyncMock(return_value=[FakeBleakDevice()])

        with patch.dict(sys.modules, bleak=_fake_bleak_module(Scanner)):
            result = t.connect()
            assert result is True

    def test_connect_raises_on_not_found(self):
        t = BleTransport(address="AA:BB:CC:DD:EE:FF")

        class Scanner:
            discover = AsyncMock(return_value=[])

        with patch.dict(sys.modules, bleak=_fake_bleak_module(Scanner)):
            with pytest.raises(RuntimeError, match="not found"):
                t.connect()


# ── Full round-trip (send + recv) ───────────────────────────────────

class TestBleRoundTrip:
    def test_send_then_recv(self):
        """send() writes to client; recv() drains buffer."""
        t = BleTransport()
        t.tx_uuid = NUS_TX_UUID
        t._client = FakeBleakClient(FakeBleakDevice())

        fake_loop = MagicMock()
        fake_loop.time.return_value = 0.0
        fake_loop.run_until_complete = MagicMock()

        # Prime the RX buffer as if a notification already arrived
        t._rx_buffer = bytearray(b"\x02\x0d\x00\x04\x00\x01\x02\x03\x04\x12\x34\x56\x78\x03")

        with patch("asyncio.get_event_loop", return_value=fake_loop):
            t.send(b"\x02\x0c\x00\x01\x00\x01\x12\x34\x03")
            data = t.recv(timeout=500)

        t._client.write_gatt_char.assert_called_once()
        assert len(data) > 0
        assert data[0:1] == b"\x02"
