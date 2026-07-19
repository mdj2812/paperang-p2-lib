"""Unit tests for paperang.printer._base — mocked transport layer."""

import struct
from unittest.mock import MagicMock

import pytest

from paperang.printer._base import PaperangPrinter, _GET_DATA
from paperang.protocol import pack_packet, CMD_GET_BATTERY, CMD_GET_STATUS
from paperang.transport import Transport


class MockTransport(Transport):
    """Controllable transport for unit tests."""

    def __init__(self, response_data=None):
        self.sent_packets = []
        self._response = response_data or b""
        self.connected = False

    def connect(self):
        self.connected = True
        return True

    def send(self, packet):
        self.sent_packets.append(packet)

    def recv(self, timeout=1000):
        return self._response

    def disconnect(self):
        self.connected = False

    def set_response(self, cmd_echo, cmd_data, data_bytes):
        """Build a proper response with echo + data frames."""
        echo = pack_packet(cmd_echo, b"")
        data = pack_packet(cmd_data, data_bytes)
        self._response = echo + data


@pytest.fixture
def printer():
    return PaperangPrinter(MockTransport())


class TestPrinterCommands:
    """Test basic printer commands via mock transport."""

    def test_feed(self, printer):
        printer.feed(50)
        assert len(printer._transport.sent_packets) == 1

    def test_feed_default(self, printer):
        printer.feed()
        assert len(printer._transport.sent_packets) == 1

    def test_set_heat_density(self, printer):
        printer.set_heat_density(80)
        assert len(printer._transport.sent_packets) == 1

    def test_set_heat_density_clamped(self, printer):
        printer.set_heat_density(150)
        assert len(printer._transport.sent_packets) == 1

    def test_set_heat_density_negative(self, printer):
        printer.set_heat_density(-10)
        assert len(printer._transport.sent_packets) == 1

    def test_set_paper_type(self, printer):
        printer.set_paper_type(0)
        assert len(printer._transport.sent_packets) == 1

    def test_set_paper_type_continuous(self, printer):
        printer.set_paper_type(1)
        assert len(printer._transport.sent_packets) == 1

    def test_print_test_page(self, printer):
        printer.print_test_page()
        assert len(printer._transport.sent_packets) == 1

    def test_feed_to_head(self, printer):
        printer.feed_to_head(200)
        assert len(printer._transport.sent_packets) == 1

    def test_print_default_para(self, printer):
        printer.print_default_para()
        assert len(printer._transport.sent_packets) == 1

    def test_disconnect_bt(self, printer):
        printer.disconnect_bt()
        assert len(printer._transport.sent_packets) == 1

    def test_set_power_down_time(self, printer):
        printer.set_power_down_time(300)
        assert len(printer._transport.sent_packets) == 1

    def test_set_max_gap(self, printer):
        printer.set_max_gap(10)
        assert len(printer._transport.sent_packets) == 1

    def test_set_factory_mode(self, printer):
        printer.set_factory_mode(1)
        assert len(printer._transport.sent_packets) == 1

    def test_set_crc_key_bytes(self, printer):
        printer.set_crc_key(b"\x01\x02\x03\x04")
        assert len(printer._transport.sent_packets) == 1

    def test_set_crc_key_int(self, printer):
        printer.set_crc_key(0x12345678)
        assert len(printer._transport.sent_packets) == 1


class TestGetCommands:
    """Test GET commands that return data."""

    def test_get_battery(self, printer):
        printer._transport.set_response(
            CMD_GET_BATTERY, CMD_GET_BATTERY + 1, b"\x64"
        )
        result = printer.get_battery()
        assert result == 100

    def test_get_battery_empty(self, printer):
        printer._transport.set_response(0x10, 0x11, b"")
        result = printer.get_battery()
        assert result is None

    def test_get_battery_no_response(self, printer):
        result = printer.get_battery()
        assert result is None

    def test_get_status(self, printer):
        printer._transport.set_response(CMD_GET_STATUS, CMD_GET_STATUS + 1, b"\x00")
        result = printer.get_status()
        assert result == "00"

    def test_get_voltage(self, printer):
        printer._transport.set_response(0x0E, 0x0F, struct.pack("<H", 4200))
        result = printer.get_voltage()
        assert result == 4200

    def test_get_voltage_none(self, printer):
        printer._transport.set_response(0x0E, 0x0F, b"")
        result = printer.get_voltage()
        assert result is None

    def test_get_temperature(self, printer):
        printer._transport.set_response(0x12, 0x13, b"\x28")
        result = printer.get_temperature()
        assert result == 0x28

    def test_get_heat_density(self, printer):
        printer._transport.set_response(0x1C, 0x1D, struct.pack("<H", 75))
        result = printer.get_heat_density()
        assert result == 75

    def test_get_power_down_time(self, printer):
        printer._transport.set_response(0x1F, 0x20, struct.pack("<H", 600))
        result = printer.get_power_down_time()
        assert result == 600

    def test_get_paper_type(self, printer):
        printer._transport.set_response(0x2A, 0x2B, b"\x00")
        result = printer.get_paper_type()
        assert result == 0

    def test_get_max_gap(self, printer):
        printer._transport.set_response(0x28, 0x29, struct.pack("<H", 5))
        result = printer.get_max_gap()
        assert result == 5

    def test_get_country(self, printer):
        printer._transport.set_response(0x2D, 0x2E, b"CN")
        result = printer.get_country()
        assert result == "CN"

    def test_get_factory_status(self, printer):
        printer._transport.set_response(0x15, 0x16, b"\x01")
        result = printer.get_factory_status()
        assert result == "01"


class TestVersionAndInfo:
    """Test version/model/serial/hardware info getters."""

    def test_get_version_ascii(self, printer):
        printer._transport.set_response(0x04, 0x05, b"1.2.3")
        result = printer.get_version()
        assert result == "1.2.3"

    def test_get_version_binary(self, printer):
        printer._transport.set_response(0x04, 0x05, b"\x00\x01")
        result = printer.get_version()
        assert result == "1"

    def test_get_version_none(self, printer):
        result = printer.get_version()
        assert result is None

    def test_get_model(self, printer):
        printer._transport.set_response(0x06, 0x07, b"P2")
        result = printer.get_model()
        assert result == "P2"

    def test_get_sn(self, printer):
        printer._transport.set_response(0x0A, 0x0B, b"SN12345")
        result = printer.get_sn()
        assert result == "SN12345"

    def test_get_board_version(self, printer):
        printer._transport.set_response(0x23, 0x24, b"v2.0")
        result = printer.get_board_version()
        assert result == "v2.0"

    def test_get_hw_info(self, printer):
        printer._transport.set_response(0x25, 0x26, b"\xFF\xEE")
        result = printer.get_hw_info()
        assert result == "ffee"

    def test_get_bt_mac(self, printer):
        printer._transport.set_response(0x08, 0x09, b"\x11\x22\x33\x44\x55\x66")
        result = printer.get_bt_mac()
        assert result == "112233445566"


class TestCleanStr:
    """Test the _clean_str static method."""

    def test_clean_normal(self):
        assert PaperangPrinter._clean_str(b"hello") == "hello"

    def test_clean_nul_terminated(self):
        assert PaperangPrinter._clean_str(b"hello\x00") == "hello"

    def test_clean_whitespace(self):
        assert PaperangPrinter._clean_str(b"  abc  ") == "abc"


class TestConnectDisconnect:
    """Test connect/disconnect delegation to transport."""

    def test_connect(self, printer):
        assert printer.connect() is True
        assert printer._transport.connected is True

    def test_disconnect(self, printer):
        printer._transport.connect()
        printer.disconnect()
        assert printer._transport.connected is False

    def test_send_basic(self, printer):
        printer.send(0x01)
        assert len(printer._transport.sent_packets) == 1

    def test_send_with_data(self, printer):
        printer.send(0x01, b"test")
        assert len(printer._transport.sent_packets) == 1

    def test_send_multi_packet(self, printer):
        printer.send_multi_packet(0x00, b"X" * 3000)
        packets = printer._transport.sent_packets
        assert len(packets) >= 3  # 3000 bytes / 1023 max per packet

    def test_read_response_empty(self, printer):
        result = printer.read_response()
        assert result == []

    def test_read_response_with_data(self, printer):
        data = pack_packet(0x0C, b"hello")
        printer._transport._response = data
        result = printer.read_response()
        assert len(result) == 1
        assert result[0]["cmd"] == 0x0C


class TestPrintBitmap:
    """Test bitmap printing."""

    def test_print_bitmap_small(self, printer):
        data = b"\xFF" * 72 * 5  # 5 lines
        printer.print_bitmap(data)
        assert len(printer._transport.sent_packets) >= 1

    def test_print_bitmap_multipacket(self, printer):
        data = b"\x00" * 72 * 20  # 20 lines → multi-packet
        printer.print_bitmap(data)
        assert len(printer._transport.sent_packets) >= 2
