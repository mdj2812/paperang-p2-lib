"""Paperang P2 USB Printer — High-level printing functions.

Image rendering, text layout, QR codes, pickup codes, and test patterns.
Built on top of :class:`paperang.printer.PaperangPrinter`.
"""

import os
import random
from PIL import Image, ImageDraw, ImageFont

from ..constants import (
    PRINT_WIDTH,
    LINE_BYTES,
    BUNDLED_FONTS_TEXT,
    BUNDLED_FONTS_PICKUP,
    BUNDLED_FONTS_CJK,
)
from ._base import PaperangPrinter
from ..transport import Transport


class PaperangP2(PaperangPrinter):
    """High-level Paperang P2 printer with image/text/QR support."""

    def __init__(self, transport: Transport | None = None,
                 font_paths_text=None, font_paths_pickup=None,
                 profiles_path=None):
        super().__init__(transport)
        self.font_paths_text = font_paths_text
        self.font_paths_pickup = font_paths_pickup
        self.profiles_path = profiles_path

    # ── High-level print functions ──────────────────────────────

    def print_image(self, image_path, heat_density=75, feed_before=50,
                    feed_after=300, threshold=128, brightness=1.0, contrast=1.0):
        """Print an image from a local file path or a remote URL."""
        if isinstance(image_path, str) and image_path.startswith(('http://', 'https://')):
            from io import BytesIO
            from urllib.request import urlopen

            with urlopen(image_path, timeout=15) as resp:
                data = resp.read()
            img = Image.open(BytesIO(data))
        else:
            img = Image.open(image_path)

        if img.width != PRINT_WIDTH:
            ratio = PRINT_WIDTH / img.width
            new_height = int(img.height * ratio)
            img = img.resize((PRINT_WIDTH, new_height), Image.LANCZOS)

        if img.mode != '1':
            img = img.convert('L')
            img = img.point(lambda x: max(0, min(255, int((x - 128) * contrast + 128 * brightness))))
            img = img.point(lambda x: 0 if x < threshold else 255, '1')

        width_bytes = PRINT_WIDTH // 8
        data = bytearray()
        for y in range(img.height):
            row = bytearray(width_bytes)
            for x in range(PRINT_WIDTH):
                if img.getpixel((x, y)) == 0:
                    byte_pos = x // 8
                    bit_pos = 7 - (x % 8)
                    row[byte_pos] |= (1 << bit_pos)
            data.extend(row)

        self.set_paper_type(0)
        self.set_heat_density(heat_density)
        self.feed(feed_before)
        self.print_bitmap(bytes(data), width_bytes)
        self.feed(feed_after)
        return True

    def _resolve_font_paths(self, font_list):
        """Resolve font paths. Handles both absolute paths and relative-to-package paths."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        resolved = []
        for f in font_list:
            if os.path.isabs(f):
                if os.path.exists(f):
                    resolved.append(f)
            else:
                path = os.path.join(base_dir, f)
                if os.path.exists(path):
                    resolved.append(path)
        return resolved

    def _get_text_fonts(self):
        """Get font paths for text printing: CJK first (if installed), then Latin."""
        if self.font_paths_text:
            return self.font_paths_text
        fonts = self._resolve_font_paths(BUNDLED_FONTS_CJK)
        fonts.extend(self._resolve_font_paths(BUNDLED_FONTS_TEXT))
        return fonts

    def print_text(self, text, font_size=24, heat_density=75):
        """Print text. CJK support requires installing with [cjk] extra."""
        font_paths = self._get_text_fonts()
        font = self._load_font(font_paths, font_size)

        lines = text.split('\n')
        max_width = 0
        total_height = 0
        line_heights = []

        for line in lines:
            bbox = font.getbbox(line)
            w = bbox[2] - bbox[0] if bbox else len(line) * font_size // 2
            h = bbox[3] if bbox else font_size
            max_width = max(max_width, w)
            line_heights.append(h + 4)
            total_height += h + 4

        img_width = PRINT_WIDTH
        img_height = ((total_height + 20 + 7) // 8) * 8
        img = Image.new('1', (img_width, img_height), 1)
        draw = ImageDraw.Draw(img)

        y = 10
        for i, line in enumerate(lines):
            draw.text((10, y), line, font=font, fill=0)
            y += line_heights[i]

        tmp_path = '/tmp/paperang_text.png'
        img.save(tmp_path)
        return self.print_image(tmp_path, heat_density=heat_density)

    def print_qr(self, content, box_size=10, heat_density=75, max_width=None):
        """Print QR code."""
        try:
            import qrcode
        except ImportError:
            print("Please install qrcode: pip3 install qrcode[pil]")
            return False

        if max_width is None:
            max_width = PRINT_WIDTH - 40

        optimal_box_size = max_width // 41
        if optimal_box_size < 4:
            optimal_box_size = 4

        qr = qrcode.QRCode(version=None, box_size=optimal_box_size, border=2)
        qr.add_data(content)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        if img.mode != 'RGB':
            img = img.convert('RGB')

        qr_size = min(img.width, img.height, max_width)
        img = img.resize((qr_size, qr_size), Image.NEAREST)
        img = img.convert('L').point(lambda x: 0 if x < 128 else 255, '1')

        canvas = Image.new('1', (PRINT_WIDTH, qr_size + 20), 1)
        offset_x = (PRINT_WIDTH - qr_size) // 2
        canvas.paste(img, (offset_x, 10))

        tmp_path = '/tmp/paperang_qr.png'
        canvas.save(tmp_path)
        return self.print_image(tmp_path, heat_density=heat_density)

    def print_pickup_code(self, code, heat_density=100):
        """Print a pickup code in large bold style (96px, centered)."""
        font_paths = self.font_paths_pickup or self._resolve_font_paths(BUNDLED_FONTS_PICKUP)
        font = self._load_font(font_paths, 96)

        bbox = font.getbbox(code)
        text_width = bbox[2] - bbox[0] if bbox else 400
        text_height = bbox[3] - bbox[0] if bbox else 120

        canvas_width = PRINT_WIDTH
        canvas_height = ((text_height + 60 + 7) // 8) * 8
        canvas = Image.new('1', (canvas_width, canvas_height), 1)
        draw = ImageDraw.Draw(canvas)

        x = (canvas_width - text_width) // 2
        y = 20
        draw.text((x, y), code, font=font, fill=0)

        tmp_path = '/tmp/paperang_pickup_code.png'
        canvas.save(tmp_path)
        return self.print_image(tmp_path, heat_density=heat_density,
                                feed_before=50, feed_after=200)

    # ── Test functions ──────────────────────────────────────────

    def print_pattern_test(self):
        """Print pattern test (line/column/multi-packet)."""
        width_bytes = LINE_BYTES
        data = bytearray()

        # Test line length - 8 columns
        for _ in range(50):
            row = bytearray(width_bytes)
            for col in range(8):
                start_byte = col * 9
                for b in range(9):
                    row[start_byte + b] = 0xFF
            data.extend(row)

        # Test dots per line - alternating 10101010
        for _ in range(50):
            row = bytearray(width_bytes)
            for b in range(width_bytes):
                row[b] = 0xAA
            data.extend(row)

        # Test dots per column - vertical lines
        for _ in range(50):
            row = bytearray(width_bytes)
            for b in range(width_bytes):
                row[b] = 0x81
            data.extend(row)

        # Random data test
        for _ in range(100):
            row = bytearray(width_bytes)
            for b in range(width_bytes):
                row[b] = random.randint(0, 255)
            data.extend(row)

        self.set_paper_type(0)
        self.set_heat_density(75)
        self.feed(50)
        self.print_bitmap(bytes(data), width_bytes)
        self.feed(300)
        return True

    def print_heat_density_test(self):
        """Print heat density test (0, 25, 50, 75, 100)."""
        width_bytes = LINE_BYTES

        for density in [0, 25, 50, 75, 100]:
            self.set_heat_density(density)
            data = bytearray()

            for _ in range(20):
                data.extend(bytearray(width_bytes))
            for _ in range(30):
                row = bytearray(width_bytes)
                for b in range(width_bytes):
                    row[b] = 0xFF
                data.extend(row)
            for _ in range(20):
                data.extend(bytearray(width_bytes))

            self.print_bitmap(bytes(data), width_bytes)
            self.feed(50)

        self.set_heat_density(75)
        self.feed(300)
        return True

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _load_font(font_paths, size):
        """Load first available font, fallback to default."""
        for fp in font_paths:
            if os.path.exists(fp):
                return ImageFont.truetype(fp, size)
        return ImageFont.load_default()
