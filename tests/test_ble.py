"""Tests for paperang.transport._ble — constructor and defaults (no BLE hardware)."""

import pytest

from paperang.transport._ble import BleTransport, NUS_SERVICE_UUID, NUS_TX_UUID, NUS_RX_UUID
from paperang.transport import Transport


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

    def test_is_transport(self):
        t = BleTransport()
        assert isinstance(t, Transport)

    def test_disconnect_no_client(self):
        t = BleTransport()
        t.disconnect()  # should not raise

    def test_rx_buffer_clear(self):
        t = BleTransport()
        t._rx_buffer.extend(b"hello")
        assert bytes(t._rx_buffer) == b"hello"
        t.disconnect()
        assert t._rx_buffer == bytearray()
