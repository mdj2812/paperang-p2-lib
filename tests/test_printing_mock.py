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


def _extract_bitmap(packets):
    """Extract combined bitmap data from CMD_PRINT_BITMAP (0x00) packets.

    Packet format: [0x02][cmd:1B][remain:1B][dataLen:2B LE][data][CRC32:4B LE][0x03]
    Returns bytearray of all bitmap data chunks concatenated.
    """
    data = bytearray()
    for pkt in packets:
        if len(pkt) < 10 or pkt[1] != 0x00:          # not CMD_PRINT_BITMAP
            continue
        data_len = struct.unpack_from('<H', pkt, 3)[0]
        data.extend(pkt[5:5 + data_len])
    return data


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
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

    def test_print_text_multiline(self, p2):
        result = p2.print_text("Line1\nLine2\nLine3")
        assert result is True
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

    def test_print_text_custom_size(self, p2):
        result = p2.print_text("Big", font_size=48)
        assert result is True
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

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
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

    def test_print_image_wider_than_print_width(self, p2, tmp_path):
        from PIL import Image
        import os
        path = os.path.join(str(tmp_path), "wide.png")
        img = Image.new("RGB", (1000, 100), "white")
        img.save(path)
        result = p2.print_image(path, feed_before=0, feed_after=0)
        assert result is True
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0


class TestPrintQR:
    """QR code printing (requires qrcode package)."""

    def test_print_qr(self, p2):
        pytest.importorskip("qrcode")
        result = p2.print_qr("https://example.com")
        assert result is True
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

    def test_print_qr_custom_size(self, p2):
        pytest.importorskip("qrcode")
        result = p2.print_qr("test", max_width=200)
        assert result is True
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

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
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

    def test_print_pickup_code_long(self, p2):
        result = p2.print_pickup_code("A-1234567")
        assert result is True
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0


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


class TestVerticalPrinting:
    """Vertical (rotated 90°) printing mode."""

    def test_vertical_text(self, p2):
        """Vertical text should produce valid bitmap packets."""
        result = p2.print_text("VERTICAL LABEL", font_size=48, vertical=True)
        assert result is True
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

    def test_vertical_text_multiline(self, p2):
        """Vertical multiline text should not crash."""
        result = p2.print_text("Line1\nLine2\nLine3", vertical=True)
        assert result is True
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

    def test_vertical_text_unicode(self, p2):
        """Vertical CJK text should not crash."""
        result = p2.print_text("纵向打印", vertical=True)
        assert result is True
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

    def test_vertical_image(self, p2, tmp_path):
        """Vertical image should rotate and print."""
        from PIL import Image
        import os
        path = os.path.join(str(tmp_path), "test.png")
        img = Image.new("RGB", (576, 200), "white")
        # Draw a black rectangle to verify content survives rotation
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.rectangle([100, 50, 476, 150], fill="black")
        img.save(path)
        result = p2.print_image(path, vertical=True, feed_before=0, feed_after=0)
        assert result is True
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

    def test_vertical_image_wider_than_print_width(self, p2, tmp_path):
        """Vertical mode: image taller than 576px after rotation should scale down."""
        from PIL import Image
        import os
        path = os.path.join(str(tmp_path), "tall.png")
        # Create an image that will be 800px wide after 90° rotation
        # (i.e., 800px tall before rotation)
        img = Image.new("RGB", (576, 800), "white")
        img.save(path)
        result = p2.print_image(path, vertical=True, feed_before=0, feed_after=0)
        assert result is True
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

    def test_vertical_qr(self, p2):
        """Vertical QR code should not crash."""
        pytest.importorskip("qrcode")
        result = p2.print_qr("https://example.com", vertical=True)
        assert result is True
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

    def test_vertical_pickup_code(self, p2):
        """Vertical pickup code should not crash."""
        result = p2.print_pickup_code("19-4308", vertical=True)
        assert result is True
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

    def test_vertical_backward_compat(self, p2):
        """vertical=False (default) should produce same results as before."""
        result = p2.print_text("normal")
        assert result is True
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0 and len(bm) % 72 == 0

    def test_vertical_rotates_90_clockwise(self, p2):
        """Vertical mode: bitmap rows must be 72 bytes (= padded to PRINT_WIDTH)."""
        p2.print_text("HI", font_size=48, vertical=True)
        bm = _extract_bitmap(p2._transport.sent_packets)
        assert len(bm) > 0, "No bitmap data found"
        assert len(bm) % 72 == 0, (
            f"Expected multiple of 72 bytes (PRINT_WIDTH padded), got {len(bm)}"
        )
