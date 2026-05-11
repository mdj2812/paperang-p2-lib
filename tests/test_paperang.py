"""Tests for paperang-p2-lib."""

import os
import pytest

from paperang.constants import (
    VENDOR_ID, PRODUCT_ID, PRINT_WIDTH, LINE_BYTES,
    BUNDLED_FONTS_TEXT, BUNDLED_FONTS_PICKUP, BUNDLED_FONTS_CJK,
)
from paperang.protocol import (
    CRC_SEED, MAX_PACKET_DATA,
    crc32_paperang, pack_packet, unpack_response,
    FRAME_HEADER, FRAME_FOOTER,
)
from paperang.printer import PaperangPrinter
from paperang.printing import PaperangP2


class TestConstants:
    """Test that constants are correctly defined."""

    def test_usb_ids(self):
        assert VENDOR_ID == 0x4348
        assert PRODUCT_ID == 0x5584

    def test_protocol_constants(self):
        assert CRC_SEED == 0x35769521 & 0xFFFFFFFF
        assert PRINT_WIDTH == 576
        assert LINE_BYTES == 72
        assert MAX_PACKET_DATA == 1023

    def test_bundled_fonts_text_is_list(self):
        assert isinstance(BUNDLED_FONTS_TEXT, list)
        assert len(BUNDLED_FONTS_TEXT) > 0

    def test_bundled_fonts_pickup_is_list(self):
        assert isinstance(BUNDLED_FONTS_PICKUP, list)
        assert len(BUNDLED_FONTS_PICKUP) > 0

    def test_bundled_fonts_cjk_is_list(self):
        """BUNDLED_FONTS_CJK is always a list (empty if [cjk] not installed)."""
        assert isinstance(BUNDLED_FONTS_CJK, list)


class TestCJKOptional:
    """Test CJK font behavior with and without [cjk] extra."""

    def test_cjk_fonts_type(self):
        """BUNDLED_FONTS_CJK is a list regardless of [cjk] installation."""
        assert isinstance(BUNDLED_FONTS_CJK, list)

    def test_latin_fonts_always_available(self):
        """Latin font files are always bundled and should exist."""
        pkg_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(pkg_dir, "..", "src", "paperang")
        for font_rel in BUNDLED_FONTS_TEXT:
            font_path = os.path.join(src_dir, font_rel)
            assert os.path.exists(font_path), f"Latin font missing: {font_path}"

    def test_pickup_fonts_always_available(self):
        """Pickup code font files are always bundled."""
        pkg_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(pkg_dir, "..", "src", "paperang")
        for font_rel in BUNDLED_FONTS_PICKUP:
            font_path = os.path.join(src_dir, font_rel)
            assert os.path.exists(font_path), f"Pickup font missing: {font_path}"


class TestResolveFontPaths:
    """Test _resolve_font_paths method."""

    def test_resolve_relative_paths(self):
        """Relative paths should be resolved relative to package directory."""
        printer = PaperangP2()
        resolved = printer._resolve_font_paths(BUNDLED_FONTS_TEXT)
        assert len(resolved) > 0
        for path in resolved:
            assert os.path.isabs(path)
            assert os.path.exists(path)

    def test_resolve_absolute_paths(self):
        """Absolute paths should be returned as-is if they exist."""
        printer = PaperangP2()
        resolved = printer._resolve_font_paths(BUNDLED_FONTS_TEXT)
        re_resolved = printer._resolve_font_paths(resolved)
        assert re_resolved == resolved

    def test_resolve_nonexistent_paths(self):
        """Non-existent paths should be filtered out."""
        printer = PaperangP2()
        result = printer._resolve_font_paths(["/nonexistent/font.ttf"])
        assert result == []


class TestLoadFont:
    """Test _load_font static method."""

    def test_load_valid_font(self):
        """Should load a valid font file."""
        printer = PaperangP2()
        resolved = printer._resolve_font_paths(BUNDLED_FONTS_TEXT)
        font = printer._load_font(resolved, 24)
        assert font is not None

    def test_load_font_fallback(self):
        """Should fall back to default font when no paths exist."""
        font = PaperangP2._load_font(["/nonexistent/path.ttf"], 24)
        assert font is not None


class TestCRCAndPacket:
    """Test CRC32 and packet packing."""

    def test_crc32_paperang(self):
        """CRC32 with custom seed should produce deterministic output."""
        data = b"hello"
        crc1 = crc32_paperang(data)
        crc2 = crc32_paperang(data)
        assert crc1 == crc2

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


class TestUnpackResponse:
    """Test response frame parsing."""

    def test_unpack_valid_frame(self):
        """Should parse a well-formed response."""
        data = b"\x01\x02\x03"
        packet = pack_packet(0x0C, data)
        result = unpack_response(packet)
        assert result is not None
        assert result['cmd'] == 0x0C
        assert result['data'] == data

    def test_unpack_too_short(self):
        assert unpack_response(b"\x02\x03") is None

    def test_unpack_bad_footer(self):
        packet = bytearray(pack_packet(0x01, b"test"))
        packet[-1] = 0xFF
        assert unpack_response(packet) is None

    def test_unpack_no_header(self):
        assert unpack_response(b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a") is None


class TestClassHierarchy:
    """Test that PaperangP2 correctly inherits from PaperangPrinter."""

    def test_p2_is_printer(self):
        assert issubclass(PaperangP2, PaperangPrinter)

    def test_printer_has_low_level(self):
        p = PaperangPrinter()
        assert hasattr(p, 'connect')
        assert hasattr(p, 'send')
        assert hasattr(p, 'send_multi_packet')
        assert hasattr(p, 'read_response')
        assert hasattr(p, 'feed')
        assert hasattr(p, 'set_heat_density')
        assert hasattr(p, 'set_paper_type')
        assert hasattr(p, 'print_bitmap')

    def test_p2_has_high_level(self):
        p = PaperangP2()
        assert hasattr(p, 'print_image')
        assert hasattr(p, 'print_text')
        assert hasattr(p, 'print_qr')
        assert hasattr(p, 'print_pickup_code')
        assert hasattr(p, 'print_pattern_test')
        assert hasattr(p, 'print_heat_density_test')

    def test_p2_inherits_low_level(self):
        """PaperangP2 should have all low-level methods too."""
        p = PaperangP2()
        assert hasattr(p, 'connect')
        assert hasattr(p, 'send')
        assert hasattr(p, 'feed')
        assert hasattr(p, 'print_bitmap')
