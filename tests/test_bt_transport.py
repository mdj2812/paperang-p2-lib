"""Tests for BtTransport — classic Bluetooth SPP transport."""

from unittest.mock import MagicMock, patch

import pytest

from paperang.transport import BtTransport


class TestBtTransportBasics:
    """Tests that don't require actual Bluetooth hardware."""

    def test_import(self):
        assert BtTransport is not None

    def test_instantiate_with_address(self):
        t = BtTransport(address="00:11:22:33:44:55")
        assert t.address == "00:11:22:33:44:55"

    def test_instantiate_without_address(self):
        t = BtTransport()
        assert t.address is None

    def test_instantiate_with_channel_and_timeout(self):
        t = BtTransport(
            address="AA:BB:CC:DD:EE:FF",
            channel=3,
            timeout=5.0,
        )
        assert t.address == "AA:BB:CC:DD:EE:FF"
        assert t._channel == 3
        assert t.timeout == 5.0

    def test_send_raises_when_not_connected(self):
        t = BtTransport(address="00:11:22:33:44:55")
        with pytest.raises(RuntimeError, match="not connected"):
            t.send(b"test")

    def test_recv_returns_empty_when_not_connected(self):
        t = BtTransport(address="00:11:22:33:44:55")
        assert t.recv() == b""

    def test_disconnect_when_not_connected(self):
        t = BtTransport(address="00:11:22:33:44:55")
        t.disconnect()  # should not raise

    def test_scan_returns_list(self):
        result = BtTransport.scan()
        assert isinstance(result, list)


class TestScanDevices:
    """Tests for BLE device scanning via bluetoothctl."""

    @patch("paperang.transport._bt.subprocess.run")
    def test_scan_finds_paperang(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = "[NEW] Device 00:15:83:EB:05:17 Paperang_P2\n"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        from paperang.transport._bt import _scan_devices
        devices = _scan_devices(timeout=1)
        assert len(devices) == 1
        assert devices[0] == ("00:15:83:EB:05:17", "Paperang_P2")

    @patch("paperang.transport._bt.subprocess.run")
    def test_scan_finds_miaomiaoji(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = "[NEW] Device AA:BB:CC:DD:EE:FF MiaoMiaoJi_P2S\n"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        from paperang.transport._bt import _scan_devices
        devices = _scan_devices(timeout=1)
        assert len(devices) == 1
        assert devices[0][1] == "MiaoMiaoJi_P2S"

    @patch("paperang.transport._bt.subprocess.run")
    def test_scan_ignores_other_devices(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = (
            "[NEW] Device 11:22:33:44:55:66 SomeSpeaker\n"
            "[NEW] Device 00:15:83:EB:05:17 Paperang_P2\n"
        )
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        from paperang.transport._bt import _scan_devices
        devices = _scan_devices(timeout=1)
        assert len(devices) == 1
        assert devices[0][0] == "00:15:83:EB:05:17"

    @patch("paperang.transport._bt.subprocess.run")
    def test_scan_empty(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        from paperang.transport._bt import _scan_devices
        devices = _scan_devices(timeout=1)
        assert devices == []

    @patch("paperang.transport._bt.subprocess.run",
           side_effect=FileNotFoundError)
    def test_scan_bluetoothctl_missing(self, mock_run):
        from paperang.transport._bt import _scan_devices
        devices = _scan_devices()
        assert devices == []


class TestFindRfcommChannel:
    """Tests for SDP channel lookup."""

    @patch("paperang.transport._bt.subprocess.run")
    def test_finds_channel_from_sdptool(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = (
            "Service Name: Paperang\n"
            "UUID 128: 0000fee7-0000-1000-8000-00805f9b34fb\n"
            '  "RFCOMM" (0x0003)\n'
            "    Channel: 5\n"
        )
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        from paperang.transport._bt import _find_rfcomm_channel
        channel = _find_rfcomm_channel("00:15:83:EB:05:17")
        assert channel == 5

    @patch("paperang.transport._bt.subprocess.run")
    def test_falls_back_to_channel_1(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = "No services found\n"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        from paperang.transport._bt import _find_rfcomm_channel
        channel = _find_rfcomm_channel("00:15:83:EB:05:17")
        assert channel == 1

    @patch("paperang.transport._bt.subprocess.run",
           side_effect=FileNotFoundError)
    def test_falls_back_when_sdptool_missing(self, mock_run):
        from paperang.transport._bt import _find_rfcomm_channel
        channel = _find_rfcomm_channel("00:15:83:EB:05:17")
        assert channel == 1


# ── Fixtures for connect tests that need a mock socket module ──

def _make_mock_socket_module():
    """Build a MagicMock that acts like a socket module on Linux with BT."""
    mock_sock_mod = MagicMock()
    mock_sock_mod.AF_BLUETOOTH = 31
    mock_sock_mod.SOCK_STREAM = 1
    mock_sock_mod.BTPROTO_RFCOMM = 3
    mock_sock_mod.timeout = __import__("socket").timeout
    mock_sock_mod.OSError = OSError
    return mock_sock_mod


class TestBtTransportConnect:
    """Tests for connect/send/recv/disconnect with mocked sockets."""

    def _patch_all(self):
        """Return (patch_ctx, mock_sock) tuple for patching socket + subprocess."""
        mock_sock_mod = _make_mock_socket_module()
        mock_sock = MagicMock()
        mock_sock_mod.socket.return_value = mock_sock
        return mock_sock_mod, mock_sock

    @patch("paperang.transport._bt.subprocess.run")
    def test_connect_with_explicit_address(self, mock_sub_run):
        from paperang.transport._bt import socket as bt_socket_module  # noqa: F811

        mock_sock_mod, mock_sock = self._patch_all()
        mock_find_channel = MagicMock(return_value=5)

        with patch.dict(
            "paperang.transport._bt.__dict__",
            {"socket": mock_sock_mod, "_find_rfcomm_channel": mock_find_channel,
             "_scan_devices": MagicMock()},
        ):
            t = BtTransport(address="00:15:83:EB:05:17")
            result = t.connect()

        assert result is True
        mock_sock_mod.socket.assert_called_once_with(31, 1, 3)
        mock_sock.connect.assert_called_once_with(("00:15:83:EB:05:17", 5))
        mock_sock.settimeout.assert_called_once_with(10.0)

    @patch("paperang.transport._bt.subprocess.run")
    def test_connect_auto_discover(self, mock_sub_run):
        mock_sock_mod, mock_sock = self._patch_all()
        mock_scan = MagicMock(return_value=[("00:15:83:EB:05:17", "Paperang_P2")])
        mock_find = MagicMock(return_value=1)

        with patch.dict(
            "paperang.transport._bt.__dict__",
            {"socket": mock_sock_mod, "_scan_devices": mock_scan,
             "_find_rfcomm_channel": mock_find},
        ):
            t = BtTransport()
            result = t.connect()

        assert result is True
        assert t.address == "00:15:83:EB:05:17"
        mock_scan.assert_called_once()

    @patch("paperang.transport._bt.subprocess.run")
    def test_connect_no_devices_found(self, mock_sub_run):
        mock_sock_mod, _ = self._patch_all()
        mock_scan = MagicMock(return_value=[])

        with patch.dict(
            "paperang.transport._bt.__dict__",
            {"socket": mock_sock_mod, "_scan_devices": mock_scan},
        ):
            t = BtTransport()
            with pytest.raises(RuntimeError, match="not found"):
                t.connect()

    @patch("paperang.transport._bt.subprocess.run")
    def test_connect_socket_error(self, mock_sub_run):
        mock_sock_mod, mock_sock = self._patch_all()
        mock_sock.connect.side_effect = OSError("Connection refused")
        mock_find = MagicMock(return_value=1)

        with patch.dict(
            "paperang.transport._bt.__dict__",
            {"socket": mock_sock_mod, "_find_rfcomm_channel": mock_find,
             "_scan_devices": MagicMock()},
        ):
            t = BtTransport(address="00:15:83:EB:05:17")
            with pytest.raises(RuntimeError, match="Failed to connect"):
                t.connect()
        mock_sock.close.assert_called_once()

    @patch("paperang.transport._bt.subprocess.run")
    def test_send_and_recv(self, mock_sub_run):
        mock_sock_mod, mock_sock = self._patch_all()
        mock_sock.recv.return_value = b"OK"
        mock_find = MagicMock(return_value=3)

        with patch.dict(
            "paperang.transport._bt.__dict__",
            {"socket": mock_sock_mod, "_find_rfcomm_channel": mock_find,
             "_scan_devices": MagicMock()},
        ):
            t = BtTransport(address="00:15:83:EB:05:17", channel=3)
            t.connect()
            t.send(b"\x01\x02\x03")
            data = t.recv(timeout=200)

        mock_sock.sendall.assert_called_once_with(b"\x01\x02\x03")
        assert data == b"OK"
        mock_sock.settimeout.assert_called_with(0.2)

    @patch("paperang.transport._bt.subprocess.run")
    def test_recv_timeout(self, mock_sub_run):
        mock_sock_mod, mock_sock = self._patch_all()
        mock_sock.recv.side_effect = mock_sock_mod.timeout("timed out")
        mock_find = MagicMock(return_value=1)

        with patch.dict(
            "paperang.transport._bt.__dict__",
            {"socket": mock_sock_mod, "_find_rfcomm_channel": mock_find,
             "_scan_devices": MagicMock()},
        ):
            t = BtTransport(address="00:15:83:EB:05:17")
            t.connect()
            data = t.recv(timeout=100)

        assert data == b""

    @patch("paperang.transport._bt.subprocess.run")
    def test_recv_oserror(self, mock_sub_run):
        mock_sock_mod, mock_sock = self._patch_all()
        mock_sock.recv.side_effect = OSError("disconnected")
        mock_find = MagicMock(return_value=1)

        with patch.dict(
            "paperang.transport._bt.__dict__",
            {"socket": mock_sock_mod, "_find_rfcomm_channel": mock_find,
             "_scan_devices": MagicMock()},
        ):
            t = BtTransport(address="00:15:83:EB:05:17")
            t.connect()
            data = t.recv(timeout=100)

        assert data == b""

    @patch("paperang.transport._bt.subprocess.run")
    def test_disconnect_closes_socket(self, mock_sub_run):
        mock_sock_mod, mock_sock = self._patch_all()
        mock_find = MagicMock(return_value=1)

        with patch.dict(
            "paperang.transport._bt.__dict__",
            {"socket": mock_sock_mod, "_find_rfcomm_channel": mock_find,
             "_scan_devices": MagicMock()},
        ):
            t = BtTransport(address="00:15:83:EB:05:17")
            t.connect()
            t.disconnect()

        mock_sock.close.assert_called_once()
        assert t._sock is None

    @patch("paperang.transport._bt.subprocess.run")
    def test_disconnect_handles_oserror(self, mock_sub_run):
        mock_sock_mod, mock_sock = self._patch_all()
        mock_sock.close.side_effect = OSError
        mock_find = MagicMock(return_value=1)

        with patch.dict(
            "paperang.transport._bt.__dict__",
            {"socket": mock_sock_mod, "_find_rfcomm_channel": mock_find,
             "_scan_devices": MagicMock()},
        ):
            t = BtTransport(address="00:15:83:EB:05:17")
            t.connect()
            t.disconnect()

        assert t._sock is None
