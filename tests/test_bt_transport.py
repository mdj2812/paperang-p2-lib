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
        t.disconnect()

    def test_scan_returns_list(self):
        result = BtTransport.scan()
        assert isinstance(result, list)


class TestScanDevices:
    """Tests for device scanning via bluetoothctl."""

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

    # ── UUID fallback tests ──

    def test_scan_uuid_fallback_finds_renamed_device(self):
        """A device with non-standard name but matching UUID is discovered."""
        from paperang.transport._bt import _scan_devices

        scan_proc = MagicMock()
        scan_proc.stdout = "[NEW] Device AA:BB:CC:DD:EE:FF MyRenamedPrinter\n"
        scan_proc.stderr = ""

        with patch("paperang.transport._bt.subprocess.run",
                   return_value=scan_proc), \
             patch("paperang.transport._bt.check_paperang_uuid",
                   return_value=True):
            devices = _scan_devices(timeout=1)

        assert len(devices) == 1
        assert devices[0] == ("AA:BB:CC:DD:EE:FF", "MyRenamedPrinter")

    def test_scan_uuid_fallback_skips_non_paperang(self):
        """A device with non-matching name and no matching UUID is excluded."""
        from paperang.transport._bt import _scan_devices

        scan_proc = MagicMock()
        scan_proc.stdout = "[NEW] Device 11:22:33:44:55:66 SomeSpeaker\n"
        scan_proc.stderr = ""

        with patch("paperang.transport._bt.subprocess.run",
                   return_value=scan_proc), \
             patch("paperang.transport._bt.check_paperang_uuid",
                   return_value=False):
            devices = _scan_devices(timeout=1)

        assert devices == []

    def test_scan_uuid_fallback_and_name_match_coexist(self):
        """Both fast path (name) and UUID fallback find devices in same scan."""
        from paperang.transport._bt import _scan_devices

        scan_proc = MagicMock()
        scan_proc.stdout = (
            "[NEW] Device 00:15:83:EB:05:17 Paperang_P2\n"
            "[NEW] Device AA:BB:CC:DD:EE:FF RenamedPrinty\n"
            "[NEW] Device 11:22:33:44:55:66 RandomSpeaker\n"
        )
        scan_proc.stderr = ""

        with patch("paperang.transport._bt.subprocess.run",
                   return_value=scan_proc), \
             patch("paperang.transport._bt.check_paperang_uuid",
                   side_effect=[True, False]):
            devices = _scan_devices(timeout=1)

        assert len(devices) == 2
        assert devices[0] == ("00:15:83:EB:05:17", "Paperang_P2")
        assert devices[1] == ("AA:BB:CC:DD:EE:FF", "RenamedPrinty")

    def testcheck_paperang_uuid_finds_service(self):
        """check_paperang_uuid returns True when bluetoothctl info shows UUID."""
        from paperang.transport._bt import check_paperang_uuid

        info_proc = MagicMock()
        info_proc.stdout = (
            "Device AA:BB:CC:DD:EE:FF\n"
            "    UUID: Vendor specific  (0000fee7-0000-1000-8000-00805f9b34fb)\n"
        )
        info_proc.stderr = ""

        with patch("paperang.transport._bt.subprocess.run",
                   return_value=info_proc):
            assert check_paperang_uuid("AA:BB:CC:DD:EE:FF") is True

    def testcheck_paperang_uuid_no_service(self):
        """check_paperang_uuid returns False for non-Paperang UUID."""
        from paperang.transport._bt import check_paperang_uuid

        info_proc = MagicMock()
        info_proc.stdout = (
            "Device 11:22:33:44:55:66\n"
            "    UUID: Audio Sink  (0000110b-0000-1000-8000-00805f9b34fb)\n"
        )
        info_proc.stderr = ""

        with patch("paperang.transport._bt.subprocess.run",
                   return_value=info_proc):
            assert check_paperang_uuid("11:22:33:44:55:66") is False

    def testcheck_paperang_uuid_timeout(self):
        """check_paperang_uuid returns False on TimeoutExpired."""
        from paperang.transport._bt import check_paperang_uuid
        import subprocess as _sp

        with patch("paperang.transport._bt.subprocess.run",
                   side_effect=_sp.TimeoutExpired(cmd="...", timeout=5)):
            assert check_paperang_uuid("DE:AD:BE:EF:00:01") is False

    def testcheck_paperang_uuid_file_not_found(self):
        """check_paperang_uuid returns False when bluetoothctl is missing."""
        from paperang.transport._bt import check_paperang_uuid

        with patch("paperang.transport._bt.subprocess.run",
                   side_effect=FileNotFoundError):
            assert check_paperang_uuid("DE:AD:BE:EF:00:02") is False


class TestFindRfcommChannel:
    """Tests for SDP channel lookup."""

    @patch("paperang.transport._bt.subprocess.run")
    def test_finds_channel_from_standard_spp(self, mock_run):
        """A model that only advertises SPP must still connect."""
        mock_proc = MagicMock()
        mock_proc.stdout = (
            "Service Name: Serial Port\n"
            "Service RecHandle: 0x10001\n"
            "Service Class ID List:\n"
            "  UUID 16: Serial Port (00001101-0000-1000-8000-00805f9b34fb)\n"
            "Protocol Descriptor List:\n"
            '  "RFCOMM" (0x0003)\n'
            "    Channel: 4\n"
        )
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        from paperang.transport._bt import _find_rfcomm_channel
        assert _find_rfcomm_channel("00:15:83:EB:05:17") == 4

    @patch("paperang.transport._bt.subprocess.run")
    def test_vendor_uuid_wins_over_spp(self, mock_run):
        """Printers advertising both keep the channel they used before."""
        mock_proc = MagicMock()
        mock_proc.stdout = (
            "Service Name: Paperang\n"
            "  UUID 128: 0000fee7-0000-1000-8000-00805f9b34fb\n"
            "    Channel: 5\n"
            "Service Name: Serial Port\n"
            "  UUID 16: Serial Port (00001101-0000-1000-8000-00805f9b34fb)\n"
            "    Channel: 7\n"
        )
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        from paperang.transport._bt import _find_rfcomm_channel
        assert _find_rfcomm_channel("00:15:83:EB:05:17") == 5

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


# ── Helper: mock the whole socket module in _bt.py namespace ──

def _bt_socket_mock():
    """Return a mock that quacks like the socket module with Bluetooth support."""
    import socket as _real_socket

    mock_mod = MagicMock()
    mock_mod.AF_BLUETOOTH = 31
    mock_mod.SOCK_STREAM = 1
    mock_mod.BTPROTO_RFCOMM = 3
    mock_mod.timeout = _real_socket.timeout
    mock_mod.OSError = OSError
    mock_mod.socket = MagicMock()
    return mock_mod


class TestBtTransportConnect:
    """Tests for connect/send/recv/disconnect with mocked sockets."""

    def test_connect_with_explicit_address(self):
        mock_mod = _bt_socket_mock()
        mock_sock = mock_mod.socket.return_value

        with (
            patch("paperang.transport._bt._find_rfcomm_channel", return_value=5),
            patch("paperang.transport._bt.socket", mock_mod),
        ):
            t = BtTransport(address="00:15:83:EB:05:17")
            result = t.connect()

        assert result is True
        mock_sock.connect.assert_called_once_with(("00:15:83:EB:05:17", 5))
        mock_sock.settimeout.assert_called_once_with(10.0)

    def test_connect_auto_discover(self):
        mock_mod = _bt_socket_mock()

        with (
            patch("paperang.transport._bt._scan_devices",
                  return_value=[("00:15:83:EB:05:17", "Paperang_P2")]),
            patch("paperang.transport._bt._find_rfcomm_channel", return_value=1),
            patch("paperang.transport._bt.socket", mock_mod),
        ):
            t = BtTransport()
            result = t.connect()

        assert result is True
        assert t.address == "00:15:83:EB:05:17"

    def test_connect_no_devices_found(self):
        mock_mod = _bt_socket_mock()

        with (
            patch("paperang.transport._bt._scan_devices", return_value=[]),
            patch("paperang.transport._bt.socket", mock_mod),
        ):
            t = BtTransport()
            with pytest.raises(RuntimeError, match="not found"):
                t.connect()

    def test_connect_socket_error(self):
        mock_mod = _bt_socket_mock()
        mock_sock = mock_mod.socket.return_value
        mock_sock.connect.side_effect = OSError("Connection refused")

        with (
            patch("paperang.transport._bt._find_rfcomm_channel", return_value=1),
            patch("paperang.transport._bt.socket", mock_mod),
        ):
            t = BtTransport(address="00:15:83:EB:05:17")
            with pytest.raises(RuntimeError, match="Failed to connect"):
                t.connect()
        mock_sock.close.assert_called_once()

    def test_send_and_recv(self):
        mock_mod = _bt_socket_mock()
        mock_sock = mock_mod.socket.return_value
        mock_sock.recv.return_value = b"OK"

        with (
            patch("paperang.transport._bt._find_rfcomm_channel", return_value=3),
            patch("paperang.transport._bt.socket", mock_mod),
        ):
            t = BtTransport(address="00:15:83:EB:05:17", channel=3)
            t.connect()
            t.send(b"\x01\x02\x03")
            data = t.recv(timeout=200)

        mock_sock.sendall.assert_called_once_with(b"\x01\x02\x03")
        assert data == b"OK"

    def test_recv_timeout_returns_empty(self):
        mock_mod = _bt_socket_mock()
        mock_sock = mock_mod.socket.return_value
        mock_sock.recv.side_effect = mock_mod.timeout("timed out")

        with (
            patch("paperang.transport._bt._find_rfcomm_channel", return_value=1),
            patch("paperang.transport._bt.socket", mock_mod),
        ):
            t = BtTransport(address="00:15:83:EB:05:17")
            t.connect()
            data = t.recv(timeout=100)

        assert data == b""

    def test_recv_oserror_returns_empty(self):
        mock_mod = _bt_socket_mock()
        mock_sock = mock_mod.socket.return_value
        mock_sock.recv.side_effect = OSError("disconnected")

        with (
            patch("paperang.transport._bt._find_rfcomm_channel", return_value=1),
            patch("paperang.transport._bt.socket", mock_mod),
        ):
            t = BtTransport(address="00:15:83:EB:05:17")
            t.connect()
            data = t.recv(timeout=100)

        assert data == b""

    def test_disconnect_closes_socket(self):
        mock_mod = _bt_socket_mock()
        mock_sock = mock_mod.socket.return_value

        with (
            patch("paperang.transport._bt._find_rfcomm_channel", return_value=1),
            patch("paperang.transport._bt.socket", mock_mod),
        ):
            t = BtTransport(address="00:15:83:EB:05:17")
            t.connect()
            t.disconnect()

        mock_sock.close.assert_called_once()
        assert t._sock is None

    def test_disconnect_handles_oserror(self):
        mock_mod = _bt_socket_mock()
        mock_sock = mock_mod.socket.return_value
        mock_sock.close.side_effect = OSError

        with (
            patch("paperang.transport._bt._find_rfcomm_channel", return_value=1),
            patch("paperang.transport._bt.socket", mock_mod),
        ):
            t = BtTransport(address="00:15:83:EB:05:17")
            t.connect()
            t.disconnect()

        assert t._sock is None


class TestModelAwareBluetooth:
    """Model metadata drives discovery and channel selection."""

    @patch("paperang.transport._bt.subprocess.run")
    def test_falls_back_to_known_devices(self, mock_run):
        """A scan with no results falls back to paired/known devices.

        Some BlueZ builds return immediately from `scan on` with only
        "SetDiscoveryFilter success" (seen on Debian 13), so the scan output
        contains nothing to parse.
        """
        scan = MagicMock()
        scan.stdout = "SetDiscoveryFilter success\n"
        scan.stderr = ""

        known = MagicMock()
        known.stdout = "Device AA:BB:CC:DD:EE:FF Paperang_D1\n"
        known.stderr = ""

        mock_run.side_effect = [scan, known]

        from paperang.transport._bt import _scan_devices

        assert _scan_devices(timeout=1) == [("AA:BB:CC:DD:EE:FF", "Paperang_D1")]

    @patch("paperang.transport._bt.subprocess.run")
    def test_scan_uses_the_blocking_bluetoothctl_timeout(self, mock_run):
        """`bluetoothctl --timeout N scan on` is used instead of `timeout N …`."""
        proc = MagicMock()
        proc.stdout = "[NEW] Device AA:BB:CC:DD:EE:FF Paperang_D1\n"
        proc.stderr = ""
        mock_run.return_value = proc

        from paperang.transport._bt import _scan_devices

        _scan_devices(timeout=3)

        assert mock_run.call_args_list[0][0][0][:4] == [
            "bluetoothctl", "--timeout", "3", "scan",
        ]

    def test_module_constants_are_the_union_of_models(self):
        from paperang.models import bt_name_prefixes, bt_service_uuids
        from paperang.transport import PAPERANG_BT_NAMES, PAPERANG_SERVICE_UUID
        from paperang.transport._bt import PAPERANG_SERVICE_UUIDS

        assert PAPERANG_BT_NAMES == set(bt_name_prefixes())
        assert PAPERANG_SERVICE_UUIDS == bt_service_uuids()
        assert PAPERANG_SERVICE_UUID in PAPERANG_SERVICE_UUIDS

    def test_p2_declares_its_bluetooth_metadata(self):
        from paperang.models import get_model

        p2 = get_model("p2")
        assert p2.supports_usb
        assert p2.supports_bluetooth
        assert "paperang" in p2.bt_name_prefixes
        assert p2.bt_rfcomm_channel is None

    def test_model_prefixes_drive_discovery(self):
        with patch("paperang.transport._bt.subprocess.run") as mock_run:
            mock_run.return_value.stdout = (
                "[NEW] Device AA:BB:CC:DD:EE:FF CustomPrinter_1\n"
                "[NEW] Device 11:22:33:44:55:66 Paperang_P2\n"
            )
            mock_run.return_value.stderr = ""

            from paperang.transport._bt import _scan_devices

            only_custom = _scan_devices(timeout=1, name_prefixes=("customprinter",))
            both = _scan_devices(
                timeout=1, name_prefixes=("customprinter", "paperang")
            )

        assert only_custom == [("AA:BB:CC:DD:EE:FF", "CustomPrinter_1")]
        assert len(both) == 2

    def test_service_uuid_override(self):
        from paperang.transport._bt import check_paperang_uuid

        info = MagicMock()
        info.stdout = "UUID: Vendor specific (11112222-3333-4444-5555-666677778888)\n"
        info.stderr = ""

        with patch("paperang.transport._bt.subprocess.run", return_value=info):
            assert check_paperang_uuid(
                "AA:BB:CC:DD:EE:FF",
                ("11112222-3333-4444-5555-666677778888",),
            )
            assert not check_paperang_uuid("AA:BB:CC:DD:EE:FF")

    def test_model_channel_is_used_without_probing(self):
        from paperang.models import PrinterModel

        model = PrinterModel(
            name="X", vid=0x4348, pids=(0x5599,), print_width=384,
            bt_rfcomm_channel=3,
        )
        mock_mod = _bt_socket_mock()
        mock_sock = mock_mod.socket.return_value

        with (
            patch("paperang.transport._bt._find_rfcomm_channel") as probe,
            patch("paperang.transport._bt.socket", mock_mod),
        ):
            transport = BtTransport(address="00:15:83:EB:05:17", model=model)
            transport.connect()

        probe.assert_not_called()
        mock_sock.connect.assert_called_once_with(("00:15:83:EB:05:17", 3))

    def test_scan_without_model_uses_the_union(self):
        with (
            patch(
                "paperang.transport._bt._scan_devices",
                return_value=[("00:15:83:EB:05:17", "Paperang_P2")],
            ) as scan,
            patch("paperang.transport._bt.socket", _bt_socket_mock()),
        ):
            BtTransport().connect()

        # No model given: discovery falls back to every registered model.
        prefixes = scan.call_args.kwargs["name_prefixes"]
        assert "paperang" in prefixes
