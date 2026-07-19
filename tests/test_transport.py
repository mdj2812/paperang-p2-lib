"""Tests for paperang.transport — physical layer."""

import pytest

from paperang.transport import Transport, UsbTransport


class TestTransportABC:
    """Transport abstract base class."""

    def test_transport_is_abstract(self):
        """Transport cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Transport()  # abstract

    def test_transport_api(self):
        """Transport defines the required interface."""
        assert hasattr(Transport, 'connect')
        assert hasattr(Transport, 'send')
        assert hasattr(Transport, 'recv')
        assert hasattr(Transport, 'disconnect')


class TestUsbTransport:
    """USB transport implementation."""

    def test_create_with_defaults(self):
        t = UsbTransport()
        assert t.vid == 0x4348
        assert t.pid == 0x5584
        assert t._dev is None
        assert t._ep_out is None
        assert t._ep_in is None

    def test_create_with_custom_ids(self):
        t = UsbTransport(vid=0x1234, pid=0x5678)
        assert t.vid == 0x1234
        assert t.pid == 0x5678

    def test_is_transport(self):
        """UsbTransport should be a Transport."""
        assert issubclass(UsbTransport, Transport)
        t = UsbTransport()
        assert isinstance(t, Transport)

    def test_disconnect_before_connect(self):
        """disconnect() should not raise when never connected."""
        t = UsbTransport()
        t.disconnect()  # no-op

    def test_has_required_methods(self):
        t = UsbTransport()
        assert hasattr(t, 'connect')
        assert hasattr(t, 'send')
        assert hasattr(t, 'recv')
        assert hasattr(t, 'disconnect')
