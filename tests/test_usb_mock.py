"""Tests for paperang.transport._usb — mocked USB device layer.

usb.core and usb.util are imported locally inside UsbTransport methods,
so we mock them at the system level (``patch("usb.core")`` etc.).
"""

from unittest.mock import MagicMock, patch

import pytest

from paperang.transport._usb import UsbTransport


@pytest.fixture
def usb_transport():
    return UsbTransport()


def _mock_usb_core():
    """Create a mock usb.core module with a mock device."""
    mock_dev = MagicMock()
    mock_dev.is_kernel_driver_active.return_value = False

    mock_cfg = MagicMock()
    mock_cfg.__getitem__.return_value = (MagicMock(),)
    mock_dev.get_active_configuration.return_value = mock_cfg

    mock_find = patch("usb.core.find", return_value=mock_dev)
    return mock_find, mock_dev


def _mock_usb_endpoints():
    """Mock usb.util with endpoint descriptors."""
    mock_util = patch("usb.util")
    m = mock_util.start()
    m.find_descriptor.return_value = MagicMock(bEndpointAddress=0x81)
    m.ENDPOINT_OUT = 0
    m.ENDPOINT_IN = 1
    m.endpoint_direction = lambda addr: addr & 0x80
    return m


class TestUsbTransportInit:
    def test_default_ids(self, usb_transport):
        assert usb_transport.vid == 0x4348
        assert usb_transport.pid == 0x5584

    def test_custom_ids(self):
        t = UsbTransport(vid=0x1234, pid=0x5678)
        assert t.vid == 0x1234
        assert t.pid == 0x5678

    def test_internal_state(self, usb_transport):
        assert usb_transport._dev is None
        assert usb_transport._ep_out is None
        assert usb_transport._ep_in is None


class TestUsbConnect:
    """connect() with mocked usb.core + usb.util."""

    def test_connect_success(self, usb_transport):
        mock_find, mock_dev = _mock_usb_core()
        mock_util = _mock_usb_endpoints()
        mock_find.start()
        try:
            result = usb_transport.connect()
            assert result is True
            mock_dev.set_configuration.assert_called_once()
            assert usb_transport._dev is mock_dev
            assert usb_transport._ep_out is not None
            assert usb_transport._ep_in is not None
        finally:
            mock_find.stop()
            mock_util.stop()

    def test_connect_not_found(self, usb_transport):
        mock_find = patch("usb.core.find", return_value=None)
        mock_find.start()
        try:
            with pytest.raises(RuntimeError, match="not found"):
                usb_transport.connect()
        finally:
            mock_find.stop()

    def test_connect_detaches_kernel_driver(self, usb_transport):
        mock_dev = MagicMock()
        mock_dev.is_kernel_driver_active.return_value = True
        mock_cfg = MagicMock()
        mock_cfg.__getitem__.return_value = (MagicMock(),)
        mock_dev.get_active_configuration.return_value = mock_cfg

        mock_find = patch("usb.core.find", return_value=mock_dev)
        mock_util = _mock_usb_endpoints()
        mock_find.start()
        try:
            usb_transport.connect()
            mock_dev.detach_kernel_driver.assert_called_once_with(0)
        finally:
            mock_find.stop()
            mock_util.stop()


class TestUsbSendRecv:
    """send() / recv() over a mocked device."""

    @pytest.fixture
    def connected(self, usb_transport):
        mock_dev = MagicMock()
        mock_dev.is_kernel_driver_active.return_value = False
        mock_cfg = MagicMock()
        mock_cfg.__getitem__.return_value = (MagicMock(),)
        mock_dev.get_active_configuration.return_value = mock_cfg

        mock_find = patch("usb.core.find", return_value=mock_dev)
        mock_util = _mock_usb_endpoints()
        mock_find.start()
        usb_transport.connect()
        yield usb_transport
        mock_find.stop()
        mock_util.stop()

    def test_send_packet(self, connected):
        packet = b"\x02\x01\x00\x00\x00test\x00\x00\x00\x00\x03"
        connected.send(packet)
        connected._dev.write.assert_called_once_with(0x81, packet)

    def test_recv_data(self, connected):
        connected._dev.read.return_value = b"\x02\x0D\x00..."
        result = connected.recv(timeout=500)
        assert result == b"\x02\x0D\x00..."
        connected._dev.read.assert_called_once_with(0x81, 64, timeout=500)

    def test_recv_default_timeout(self, connected):
        connected._dev.read.return_value = b"x"
        connected.recv()
        connected._dev.read.assert_called_once_with(0x81, 64, timeout=1000)

    def test_recv_usb_error(self, connected):
        import usb.core
        connected._dev.read.side_effect = usb.core.USBError("timeout")
        result = connected.recv()
        assert result == b""


class TestUsbDisconnect:
    """disconnect() and resource cleanup."""

    def test_disconnect_before_connect(self, usb_transport):
        usb_transport.disconnect()

    def test_disconnect_releases(self, usb_transport):
        mock_find, mock_dev = _mock_usb_core()
        mock_util = _mock_usb_endpoints()
        mock_find.start()
        try:
            usb_transport.connect()
            usb_transport.disconnect()
            # dispose_resources stored on _mock_usb_endpoints()'s MagicMock
            mock_util.dispose_resources.assert_called_once_with(mock_dev)
            assert usb_transport._dev is None
            assert usb_transport._ep_out is None
            assert usb_transport._ep_in is None
        finally:
            mock_find.stop()
            mock_util.stop()

    def test_disconnect_swallows_errors(self, usb_transport):
        mock_find, mock_dev = _mock_usb_core()
        mock_util = _mock_usb_endpoints()
        mock_find.start()
        try:
            usb_transport.connect()
            with patch("usb.util.dispose_resources",
                       side_effect=RuntimeError("oops")):
                usb_transport.disconnect()  # should not raise
            assert usb_transport._dev is None
        finally:
            mock_find.stop()
            mock_util.stop()
