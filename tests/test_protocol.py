"""Tests for paperang.protocol — packet framing, CRC, command codes."""

import struct

from paperang.protocol import (
    CRC_SEED, MAX_PACKET_DATA,
    crc32_paperang, pack_packet, unpack_response,
    FRAME_HEADER, FRAME_FOOTER,
)


class TestCRC32:
    """CRC32 with Paperang-specific seed."""

    def test_crc32_paperang(self):
        """CRC32 with custom seed should produce deterministic output."""
        data = b"hello"
        crc1 = crc32_paperang(data)
        crc2 = crc32_paperang(data)
        assert crc1 == crc2

    def test_crc32_different_data(self):
        """Different data should produce different CRC."""
        assert crc32_paperang(b"a") != crc32_paperang(b"b")

    def test_crc32_empty(self):
        """Empty data should not raise."""
        result = crc32_paperang(b"")
        assert isinstance(result, int)

    def test_protocol_constants(self):
        assert CRC_SEED == 0x35769521 & 0xFFFFFFFF
        assert MAX_PACKET_DATA == 1023


class TestPackPacket:
    """Packet encoding."""

    def test_pack_packet_structure(self):
        """Packed packet should have correct structure."""
        cmd = 0x01
        data = b"\x00\x01\x02"
        packet = pack_packet(cmd, data)

        assert packet[0] == FRAME_HEADER
        assert packet[1] == cmd
        assert packet[-1] == FRAME_FOOTER
        assert len(packet) > 5

    def test_pack_packet_with_remain(self):
        """Packet with packet_remain should encode correctly."""
        packet = pack_packet(0x00, b"test", 5)
        assert packet[2] == 5

    def test_pack_no_data(self):
        packet = pack_packet(0x04, b"")
        assert packet[0] == FRAME_HEADER
        assert packet[1] == 0x04
        assert packet[2] == 0x00  # packet_remain
        assert packet[-1] == FRAME_FOOTER

    def test_pack_max_data(self):
        """Pack with max single-packet data."""
        data = b"\xFF" * MAX_PACKET_DATA
        packet = pack_packet(0x00, data)
        assert len(packet) == 1 + 1 + 1 + 2 + MAX_PACKET_DATA + 4 + 1
        # Data length field should match
        data_len = struct.unpack('<H', packet[3:5])[0]
        assert data_len == MAX_PACKET_DATA


class TestUnpackResponse:
    """Response frame parsing."""

    def test_unpack_valid_frame(self):
        """Should parse a well-formed response as a list with one frame."""
        data = b"\x01\x02\x03"
        packet = pack_packet(0x0C, data)
        result = unpack_response(packet)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['cmd'] == 0x0C
        assert result[0]['data'] == data

    def test_unpack_too_short(self):
        assert unpack_response(b"\x02\x03") == []

    def test_unpack_bad_footer(self):
        packet = bytearray(pack_packet(0x01, b"test"))
        packet[-1] = 0xFF
        assert unpack_response(packet) == []

    def test_unpack_no_header(self):
        assert unpack_response(b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a") == []

    def test_unpack_multiple_frames(self):
        """Two frames packed together should both be parsed."""
        frame1 = pack_packet(0x0C, b"echo")
        frame2 = pack_packet(0x11, b"data")
        result = unpack_response(frame1 + frame2)
        assert len(result) == 2
        assert result[0]['cmd'] == 0x0C
        assert result[1]['cmd'] == 0x11
        assert result[1]['data'] == b"data"

    def test_unpack_empty_bytes(self):
        assert unpack_response(b"") == []
