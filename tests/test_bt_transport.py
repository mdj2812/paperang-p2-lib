"""Tests for BtTransport — classic Bluetooth SPP transport."""

import pytest

from paperang.transport import BtTransport


class TestBtTransportBasics:
    """Tests that don't require actual Bluetooth hardware."""

    def test_import(self):
        """BtTransport should be importable."""
        assert BtTransport is not None

    def test_instantiate_with_address(self):
        """Can instantiate with an explicit address."""
        t = BtTransport(address="00:11:22:33:44:55")
        assert t.address == "00:11:22:33:44:55"

    def test_instantiate_without_address(self):
        """Can instantiate without address (will scan on connect)."""
        t = BtTransport()
        assert t.address is None

    def test_instantiate_with_channel_and_timeout(self):
        """Can instantiate with all optional params."""
        t = BtTransport(
            address="AA:BB:CC:DD:EE:FF",
            channel=3,
            timeout=5.0,
        )
        assert t.address == "AA:BB:CC:DD:EE:FF"
        assert t._channel == 3
        assert t.timeout == 5.0

    def test_send_raises_when_not_connected(self):
        """send() should raise RuntimeError when not connected."""
        t = BtTransport(address="00:11:22:33:44:55")
        with pytest.raises(RuntimeError, match="not connected"):
            t.send(b"test")

    def test_recv_returns_empty_when_not_connected(self):
        """recv() should return empty bytes when not connected."""
        t = BtTransport(address="00:11:22:33:44:55")
        assert t.recv() == b""

    def test_disconnect_when_not_connected(self):
        """disconnect() should not raise when not connected."""
        t = BtTransport(address="00:11:22:33:44:55")
        t.disconnect()  # should not raise

    def test_scan_returns_list(self):
        """scan() should return a list (may be empty without BT)."""
        result = BtTransport.scan()
        assert isinstance(result, list)
