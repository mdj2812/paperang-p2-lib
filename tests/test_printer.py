"""Tests for paperang.printer — application layer (printer, fonts, profiles)."""

import os

from paperang.constants import (
    VENDOR_ID, PRODUCT_ID, PRINT_WIDTH, LINE_BYTES,
    BUNDLED_FONTS_TEXT, BUNDLED_FONTS_PICKUP, BUNDLED_FONTS_CJK,
)
from paperang.printer import PaperangPrinter, PaperangP2


class TestConstants:
    """Test that constants are correctly defined."""

    def test_usb_ids(self):
        assert VENDOR_ID == 0x4348
        assert PRODUCT_ID == 0x5584

    def test_dimensions(self):
        assert PRINT_WIDTH == 576
        assert LINE_BYTES == 72

    def test_bundled_fonts_text_is_list(self):
        assert isinstance(BUNDLED_FONTS_TEXT, list)
        assert len(BUNDLED_FONTS_TEXT) > 0

    def test_bundled_fonts_pickup_is_list(self):
        assert isinstance(BUNDLED_FONTS_PICKUP, list)
        assert len(BUNDLED_FONTS_PICKUP) > 0

    def test_bundled_fonts_cjk_is_list(self):
        """BUNDLED_FONTS_CJK is always a list (empty if [cjk] not installed)."""
        assert isinstance(BUNDLED_FONTS_CJK, list)


class TestFontAvailability:
    """Test font file availability."""

    def test_latin_fonts_exist(self):
        pkg_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(pkg_dir, "..", "src", "paperang")
        for font_rel in BUNDLED_FONTS_TEXT:
            font_path = os.path.join(src_dir, font_rel)
            assert os.path.exists(font_path), f"Missing: {font_path}"

    def test_pickup_fonts_exist(self):
        pkg_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(pkg_dir, "..", "src", "paperang")
        for font_rel in BUNDLED_FONTS_PICKUP:
            font_path = os.path.join(src_dir, font_rel)
            assert os.path.exists(font_path), f"Missing: {font_path}"


class TestResolveFontPaths:
    """PaperangP2._resolve_font_paths()."""

    def test_resolve_relative(self):
        printer = PaperangP2()
        resolved = printer._resolve_font_paths(BUNDLED_FONTS_TEXT)
        assert len(resolved) > 0
        for path in resolved:
            assert os.path.isabs(path)
            assert os.path.exists(path)

    def test_resolve_absolute(self):
        printer = PaperangP2()
        resolved = printer._resolve_font_paths(BUNDLED_FONTS_TEXT)
        re_resolved = printer._resolve_font_paths(resolved)
        assert re_resolved == resolved

    def test_resolve_missing(self):
        printer = PaperangP2()
        result = printer._resolve_font_paths(["/nonexistent/font.ttf"])
        assert result == []


class TestLoadFont:
    """PaperangP2._load_font()."""

    def test_load_valid_font(self):
        printer = PaperangP2()
        resolved = printer._resolve_font_paths(BUNDLED_FONTS_TEXT)
        font = printer._load_font(resolved, 24)
        assert font is not None

    def test_fallback_on_missing(self):
        font = PaperangP2._load_font(["/nonexistent/path.ttf"], 24)
        assert font is not None


class TestClassHierarchy:
    """PaperangP2 ← PaperangPrinter inheritance."""

    def test_p2_is_printer(self):
        assert issubclass(PaperangP2, PaperangPrinter)

    def test_printer_methods(self):
        p = PaperangPrinter()
        for attr in ('connect', 'send', 'send_multi_packet', 'read_response',
                     'feed', 'set_heat_density', 'set_paper_type', 'print_bitmap',
                     'disconnect'):
            assert hasattr(p, attr), attr

    def test_p2_methods(self):
        p = PaperangP2()
        for attr in ('print_image', 'print_text', 'print_qr',
                     'print_pickup_code', 'print_pattern_test',
                     'print_heat_density_test'):
            assert hasattr(p, attr), attr

    def test_p2_inherits_low_level(self):
        p = PaperangP2()
        for attr in ('connect', 'send', 'feed', 'print_bitmap', 'disconnect'):
            assert hasattr(p, attr), attr

    def test_defaults_to_usb_transport(self):
        p = PaperangPrinter()
        from paperang.transport import UsbTransport
        assert isinstance(p._transport, UsbTransport)

    def test_custom_transport(self):
        from paperang.transport import Transport

        class DummyTransport(Transport):
            def connect(self): return True
            def send(self, packet): pass
            def recv(self, timeout=1000): return b""
            def disconnect(self): pass

        p = PaperangPrinter(DummyTransport())
        assert isinstance(p._transport, DummyTransport)
