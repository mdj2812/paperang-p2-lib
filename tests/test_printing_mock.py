"""Tests for paperang.printer._printing — high-level print functions with mock transport."""

import os
import struct
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from paperang.constants import PRINT_WIDTH, LINE_BYTES
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


@pytest.fixture
def p2():
    from paperang.printer._printing import PaperangP2
    return PaperangP2(MockTransport())


class TestPatternTest:
    """Pattern test doesn't need PIL."""

    def test_pattern_test(self, p2):
        result = p2.print_pattern_test()
        assert result is True
        assert len(p2._transport.sent_packets) > 0


class TestHeatDensityTest:
    """Heat density test doesn't need PIL."""

    def test_heat_density_test(self, p2):
        result = p2.print_heat_density_test()
        assert result is True
        assert len(p2._transport.sent_packets) > 0


class TestPrintText:
    """Text printing with real PIL rendering."""

    def test_print_text_simple(self, p2):
        result = p2.print_text("Hello")
        assert result is True
        assert len(p2._transport.sent_packets) > 0

    def test_print_text_multiline(self, p2):
        result = p2.print_text("Line1\nLine2\nLine3")
        assert result is True
        assert len(p2._transport.sent_packets) > 0

    def test_print_text_custom_size(self, p2):
        result = p2.print_text("Big", font_size=48)
        assert result is True

    def test_print_text_unicode(self, p2):
        """Chinese characters should not crash (may fallback to default font)."""
        result = p2.print_text("你好世界")
        assert result is True


class TestPrintImage:
    """Image printing tests."""

    def _make_test_image(self, path):
        from PIL import Image
        img = Image.new("RGB", (576, 100), "white")
        img.save(path)

    def test_print_image_file(self, p2, tmp_path):
        import tempfile
        import os
        path = os.path.join(str(tmp_path), "test.png")
        self._make_test_image(path)
        result = p2.print_image(path, feed_before=0, feed_after=0)
        assert result is True
        assert len(p2._transport.sent_packets) > 0

    def test_print_image_wider_than_print_width(self, p2, tmp_path):
        from PIL import Image
        import os
        path = os.path.join(str(tmp_path), "wide.png")
        img = Image.new("RGB", (1000, 100), "white")
        img.save(path)
        result = p2.print_image(path, feed_before=0, feed_after=0)
        assert result is True


class TestPrintQR:
    """QR code printing (requires qrcode package)."""

    def test_print_qr(self, p2):
        pytest.importorskip("qrcode")
        result = p2.print_qr("https://example.com")
        assert result is True
        assert len(p2._transport.sent_packets) > 0

    def test_print_qr_custom_size(self, p2):
        pytest.importorskip("qrcode")
        result = p2.print_qr("test", max_width=200)
        assert result is True

    def test_print_qr_missing_lib(self, p2):
        """Should return False when qrcode is not installed."""
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "qrcode":
                raise ImportError("No module named 'qrcode'")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            # Need fresh import of PaperangP2 after mocking
            import importlib
            import paperang.printer._printing as pm
            importlib.reload(pm)
            p = pm.PaperangP2(MockTransport())
            result = p.print_qr("test")
            assert result is False
        finally:
            builtins.__import__ = real_import


class TestPrintPickupCode:
    """Pickup code printing."""

    def test_print_pickup_code(self, p2):
        result = p2.print_pickup_code("19-4308")
        assert result is True
        assert len(p2._transport.sent_packets) > 0

    def test_print_pickup_code_long(self, p2):
        result = p2.print_pickup_code("A-1234567")
        assert result is True


class TestCustomFontPaths:
    """Custom font path configuration."""

    def test_custom_text_fonts(self):
        from paperang.printer._printing import PaperangP2
        p = PaperangP2(MockTransport(), font_paths_text=["/nonexistent/font.ttf"])
        assert p.font_paths_text == ["/nonexistent/font.ttf"]

    def test_custom_pickup_fonts(self):
        from paperang.printer._printing import PaperangP2
        p = PaperangP2(
            MockTransport(),
            font_paths_pickup=["/nonexistent/pickup.ttf"],
        )
        assert p.font_paths_pickup == ["/nonexistent/pickup.ttf"]
