"""Paperang P2 USB Printer — low-level communication layer.

Handles USB connection, packet send/receive, and basic printer commands.
"""

import struct
import usb.core
import usb.util

from .constants import VENDOR_ID, PRODUCT_ID
from .protocol import (
    pack_packet,
    unpack_response,
    CMD_PRINT_BITMAP,
    CMD_GET_STATUS,
    CMD_GET_BATTERY,
    CMD_PRINT_TEST,
    CMD_SET_HEAT,
    CMD_FEED_PAPER,
    CMD_SET_PAPER,
    CMD_GET_VOLTAGE,
    CMD_GET_TEMP,
    CMD_GET_VERSION,
    CMD_GET_MODEL,
    CMD_GET_BT_MAC,
    CMD_GET_SN,
    CMD_GET_HEAT,
    CMD_GET_POWER_DOWN,
    CMD_GET_BOARD_VERSION,
    CMD_GET_HW_INFO,
    CMD_GET_MAX_GAP,
    CMD_GET_PAPER_TYPE,
    CMD_GET_COUNTRY,
    CMD_GET_FACTORY,
    CMD_SET_FACTORY,
    CMD_SET_CRC_KEY,
    CMD_SET_POWER_DOWN,
    CMD_FEED_TO_HEAD,
    CMD_PRINT_DEFAULT_PARA,
    CMD_SET_MAX_GAP,
    CMD_DISCONNECT_BT,
    MAX_PACKET_DATA,
)

# All "get" commands require a single data byte
_GET_DATA = struct.pack('<B', 1)


class PaperangPrinter:
    """Low-level Paperang P2 USB printer interface."""

    def __init__(self):
        self.dev = None
        self.ep_out = None
        self.ep_in = None

    # ── Connection ──────────────────────────────────────────────

    def connect(self):
        """Connect to printer via USB."""
        self.dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if self.dev is None:
            raise RuntimeError("Paperang P2 printer not found")

        if self.dev.is_kernel_driver_active(0):
            self.dev.detach_kernel_driver(0)

        self.dev.set_configuration()
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]

        self.ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e:
                usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )
        self.ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e:
                usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
        )
        return True

    # ── Low-level communication ─────────────────────────────────

    def send(self, cmd, data=b''):
        """Send a single command packet."""
        packet = pack_packet(cmd, data)
        self.dev.write(self.ep_out.bEndpointAddress, packet)
        return True

    def send_multi_packet(self, cmd, data):
        """Send multi-packet data, max 1023 bytes per packet."""
        total_len = len(data)
        offset = 0

        while offset < total_len:
            remaining = total_len - offset
            chunk_len = min(MAX_PACKET_DATA, remaining)
            next_offset = offset + chunk_len
            packets_remain = (total_len - next_offset + MAX_PACKET_DATA - 1) // MAX_PACKET_DATA

            chunk = data[offset:next_offset]
            packet = pack_packet(cmd, chunk, packets_remain)
            self.dev.write(self.ep_out.bEndpointAddress, packet)
            offset = next_offset

        return True

    def read_response(self, timeout=1000):
        """Read and parse response from printer."""
        try:
            resp = self.dev.read(self.ep_in.bEndpointAddress, 64, timeout=timeout)
            return unpack_response(resp)
        except Exception:
            return None

    def _send_get(self, cmd):
        """Helper: send a GET command with data byte 0x01 and return response data."""
        self.send(cmd, _GET_DATA)
        resp = self.read_response()
        return resp['data'] if resp and resp['data'] else None

    # ── Printer controls ────────────────────────────────────────

    def feed(self, lines=100):
        """Feed paper (command 0x1A)."""
        return self.send(CMD_FEED_PAPER, struct.pack('<H', lines))

    def set_heat_density(self, density=75):
        """Set heat density 0-100 (command 0x19)."""
        density = max(0, min(100, density))
        return self.send(CMD_SET_HEAT, struct.pack('<H', density))

    def set_paper_type(self, paper_type=0):
        """Set paper type (0=normal, 1=continuous) (command 0x2C)."""
        return self.send(CMD_SET_PAPER, bytes([paper_type]))

    def print_test_page(self):
        """Print test page (command 0x1B)."""
        return self.send(CMD_PRINT_TEST)

    def feed_to_head(self, lines=100):
        """Feed paper to print head position (command 0x21)."""
        return self.send(CMD_FEED_TO_HEAD, struct.pack('<H', lines))

    def print_default_para(self):
        """Print default parameters page (command 0x22)."""
        return self.send(CMD_PRINT_DEFAULT_PARA)

    # ── GET status/info commands ────────────────────────────────

    def get_status(self):
        """Get printer status (command 0x0C). Returns hex string."""
        data = self._send_get(CMD_GET_STATUS)
        return data.hex() if data else None

    def get_battery(self):
        """Get battery level (command 0x10). Returns int or None."""
        data = self._send_get(CMD_GET_BATTERY)
        return data[0] if data and len(data) > 0 else None

    def get_voltage(self):
        """Get battery voltage in mV (command 0x0E). Returns int or None."""
        data = self._send_get(CMD_GET_VOLTAGE)
        return struct.unpack('<H', data)[0] if data and len(data) >= 2 else None

    def get_temperature(self):
        """Get printer temperature (command 0x12). Returns int or None."""
        data = self._send_get(CMD_GET_TEMP)
        return data[0] if data and len(data) > 0 else None

    def get_heat_density(self):
        """Get current heat density (command 0x1C). Returns int or None."""
        data = self._send_get(CMD_GET_HEAT)
        return struct.unpack('<H', data)[0] if data and len(data) >= 2 else None

    def get_power_down_time(self):
        """Get auto power-down time in seconds (command 0x1F). Returns int or None."""
        data = self._send_get(CMD_GET_POWER_DOWN)
        return struct.unpack('<H', data)[0] if data and len(data) >= 2 else None

    def get_paper_type(self):
        """Get current paper type (command 0x2A). Returns int or None."""
        data = self._send_get(CMD_GET_PAPER_TYPE)
        return data[0] if data and len(data) > 0 else None

    def get_max_gap(self):
        """Get max gap length (command 0x28). Returns int or None."""
        data = self._send_get(CMD_GET_MAX_GAP)
        return struct.unpack('<H', data)[0] if data and len(data) >= 2 else None

    def get_country(self):
        """Get country name (command 0x2D). Returns string or None."""
        data = self._send_get(CMD_GET_COUNTRY)
        return data.decode('utf-8', errors='replace') if data else None

    # ── GET version/hardware info ───────────────────────────────

    def get_version(self):
        """Get firmware version (command 0x04). Returns string or None."""
        data = self._send_get(CMD_GET_VERSION)
        return data.decode('utf-8', errors='replace') if data else None

    def get_model(self):
        """Get printer model (command 0x06). Returns string or None."""
        data = self._send_get(CMD_GET_MODEL)
        return data.decode('utf-8', errors='replace') if data else None

    def get_bt_mac(self):
        """Get Bluetooth MAC address (command 0x08). Returns hex string or None."""
        data = self._send_get(CMD_GET_BT_MAC)
        return data.hex() if data else None

    def get_sn(self):
        """Get serial number (command 0x0A). Returns string or None."""
        data = self._send_get(CMD_GET_SN)
        return data.decode('utf-8', errors='replace') if data else None

    def get_board_version(self):
        """Get board version (command 0x23). Returns string or None."""
        data = self._send_get(CMD_GET_BOARD_VERSION)
        return data.decode('utf-8', errors='replace') if data else None

    def get_hw_info(self):
        """Get hardware info (command 0x25). Returns hex string or None."""
        data = self._send_get(CMD_GET_HW_INFO)
        return data.hex() if data else None

    def get_factory_status(self):
        """Get factory status (command 0x15). Returns hex string or None."""
        data = self._send_get(CMD_GET_FACTORY)
        return data.hex() if data else None

    # ── SET commands ────────────────────────────────────────────

    def set_power_down_time(self, seconds):
        """Set auto power-down time in seconds (command 0x1E)."""
        return self.send(CMD_SET_POWER_DOWN, struct.pack('<H', seconds))

    def set_max_gap(self, gap):
        """Set max gap length (command 0x27)."""
        return self.send(CMD_SET_MAX_GAP, struct.pack('<H', gap))

    def set_crc_key(self, key):
        """Set CRC key (command 0x18). Key should be 4 bytes."""
        return self.send(CMD_SET_CRC_KEY, key if isinstance(key, bytes) else struct.pack('<I', key))

    def set_factory_mode(self, mode):
        """Set factory status (command 0x14)."""
        return self.send(CMD_SET_FACTORY, bytes([mode]))

    def disconnect_bt(self):
        """Disconnect Bluetooth (command 0x2F)."""
        return self.send(CMD_DISCONNECT_BT)

    # ── Bitmap printing ─────────────────────────────────────────

    def print_bitmap(self, bitmap_data, width_bytes=72):
        """Print raw bitmap data (row-based, 14 lines per packet)."""
        lines_per_packet = MAX_PACKET_DATA // width_bytes  # 14

        total_bytes = len(bitmap_data)
        total_lines = total_bytes // width_bytes
        total_packets = (total_lines + lines_per_packet - 1) // lines_per_packet

        offset = 0
        line_offset = 0
        packet_idx = 0

        while offset < total_bytes:
            remaining_lines = total_lines - line_offset
            current_lines = min(lines_per_packet, remaining_lines)
            current_bytes = current_lines * width_bytes

            packet_idx += 1
            remaining_packets = total_packets - packet_idx

            chunk = bitmap_data[offset:offset + current_bytes]
            packet = pack_packet(CMD_PRINT_BITMAP, chunk, remaining_packets)
            self.dev.write(self.ep_out.bEndpointAddress, packet)

            offset += current_bytes
            line_offset += current_lines

        return True
