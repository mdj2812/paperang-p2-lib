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
    MAX_PACKET_DATA,
)


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

    # ── Printer controls ────────────────────────────────────────

    def feed(self, lines=100):
        """Feed paper (command 0x1A)."""
        return self.send(CMD_FEED_PAPER, struct.pack('<H', lines))

    def set_heat_density(self, density=75):
        """Set heat density 0-100 (command 0x19)."""
        density = max(0, min(100, density))
        return self.send(CMD_SET_HEAT, struct.pack('<H', density))

    def set_paper_type(self, paper_type=0):
        """Set paper type (0=normal, 1=continuous)."""
        return self.send(CMD_SET_PAPER, bytes([paper_type]))

    def print_test_page(self):
        """Print test page."""
        return self.send(CMD_PRINT_TEST)

    def get_status(self):
        """Get printer status."""
        self.send(CMD_GET_STATUS, struct.pack('<B', 1))
        resp = self.read_response()
        if resp:
            return resp['data'].hex() if resp['data'] else None
        return None

    def get_battery(self):
        """Get battery level."""
        self.send(CMD_GET_BATTERY, struct.pack('<B', 1))
        resp = self.read_response()
        if resp and resp['data']:
            return resp['data'][0] if len(resp['data']) > 0 else None
        return None

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
