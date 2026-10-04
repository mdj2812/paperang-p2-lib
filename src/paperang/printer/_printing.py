"""Paperang P2 USB Printer — High-level printing functions.

Image rendering, text layout, QR codes, pickup codes, and test patterns.
Built on top of :class:`paperang.printer.PaperangPrinter`.
"""

import os
import random
from PIL import Image, ImageDraw, ImageFont

from ..constants import (
    BUNDLED_FONTS_TEXT,
    BUNDLED_FONTS_PICKUP,
    BUNDLED_FONTS_CJK,
    DEFAULT_FEED_AFTER,
    DEFAULT_FEED_BEFORE,
    DEFAULT_HEAT_DENSITY,
)
from ._base import PaperangPrinter
from ..transport import Transport


class PaperangP2(PaperangPrinter):
    """High-level Paperang printer with image/text/QR support.

    Despite the historical name this class is not P2-specific: pass ``model``
    to drive another Paperang model (see :mod:`paperang.models`).  Print
    geometry is read from the resolved model, never from module constants.
    """

    def __init__(self, transport: Transport | None = None,
                 font_paths_text=None, font_paths_pickup=None,
                 profiles_path=None, model=None):
        super().__init__(transport, model=model)
        self.font_paths_text = font_paths_text
        self.font_paths_pickup = font_paths_pickup
        self.profiles_path = profiles_path

    # ── High-level print functions ──────────────────────────────

    def print_image(self, image_path, heat_density=None, feed_before=None,
                    feed_after=None, threshold=128, brightness=1.0, contrast=1.0,
                    vertical=False):
        """Print an image from a local file path or a remote URL.

        Args:
            image_path: Local file path or HTTP(S) URL to a PNG/JPEG image.
            heat_density: 0-100 thermal print density.  Defaults to
                DEFAULT_HEAT_DENSITY; a print profile usually overrides it.
            feed_before: Lines of paper feed before printing.  Defaults to
                DEFAULT_FEED_BEFORE.
            feed_after: Lines of paper feed after printing.  Defaults to
                DEFAULT_FEED_AFTER.
            threshold: Binarization threshold (0-255).
            brightness: Brightness multiplier (1.0 = unchanged).
            contrast: Contrast adjustment (1.0 = unchanged).
            vertical: If True, rotate the image 90° clockwise
                (text reads top-to-bottom along the paper strip).
                Useful for labels and vertical receipts.
        """
        if heat_density is None:
            heat_density = DEFAULT_HEAT_DENSITY
        if feed_before is None:
            feed_before = DEFAULT_FEED_BEFORE
        if feed_after is None:
            feed_after = DEFAULT_FEED_AFTER

        if isinstance(image_path, str) and image_path.startswith(('http://', 'https://')):
            from io import BytesIO
            from urllib.request import urlopen

            with urlopen(image_path, timeout=15) as resp:
                data = resp.read()
            img = Image.open(BytesIO(data))
        else:
            img = Image.open(image_path)

        if not vertical:
            # Normal horizontal printing: scale to print-head width
            if img.width != self.print_width:
                ratio = self.print_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((self.print_width, new_height), Image.LANCZOS)
        else:
            # Rotate 90° clockwise BEFORE binarization to avoid mode-'1' artifacts.
            img = img.transpose(Image.ROTATE_270)
            # If the rotated image is wider than the print head, scale it down.
            if img.width > self.print_width:
                ratio = self.print_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((self.print_width, new_height), Image.LANCZOS)

        if img.mode != '1':
            img = img.convert('L')
            img = img.point(lambda x: max(0, min(255, int((x - 128) * contrast + 128 * brightness))))
            img = img.point(lambda x: 0 if x < threshold else 255, '1')

        if vertical and img.width < self.print_width:
            # Paste the narrow rotated image onto a full-width white canvas
            # so the printer receives full-width rows for this model.
            canvas = Image.new('1', (self.print_width, img.height), 1)
            offset_x = (self.print_width - img.width) // 2
            canvas.paste(img, (offset_x, 0))
            img = canvas

        img_width = img.width
        width_bytes = img_width // 8
        data = bytearray()
        for y in range(img.height):
            row = bytearray(width_bytes)
            for x in range(img_width):
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

    def print_text(self, text, font_size=24, heat_density=None, vertical=False):
        """Print text. CJK support requires installing with [cjk] extra.

        Args:
            heat_density: 0-100 thermal print density.  Defaults to
                DEFAULT_HEAT_DENSITY; a print profile usually overrides it.
            vertical: If True, text is rotated 90° clockwise to print
                along the paper strip length. Larger font sizes (48–96)
                produce dramatic vertical labels.
        """
        if heat_density is None:
            heat_density = DEFAULT_HEAT_DENSITY

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

        img_width = max_width + 20 if vertical else self.print_width
        img_height = ((total_height + 20 + 7) // 8) * 8
        img = Image.new('1', (img_width, img_height), 1)
        draw = ImageDraw.Draw(img)

        y = 10
        for i, line in enumerate(lines):
            draw.text((10, y), line, font=font, fill=0)
            y += line_heights[i]

        tmp_path = '/tmp/paperang_text.png'
        img.save(tmp_path)
        return self.print_image(tmp_path, heat_density=heat_density, vertical=vertical)

    def print_qr(self, content, box_size=10, heat_density=None, max_width=None,
                 vertical=False):
        """Print QR code.

        Args:
            heat_density: 0-100 thermal print density.  Defaults to
                DEFAULT_HEAT_DENSITY; a print profile usually overrides it.
            vertical: If True, rotate 90° clockwise for vertical printing.
        """
        if heat_density is None:
            heat_density = DEFAULT_HEAT_DENSITY

        try:
            import qrcode
        except ImportError:
            print("Please install qrcode: pip3 install qrcode[pil]")
            return False

        if max_width is None:
            max_width = self.print_width - 40

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

        canvas = Image.new('1', (self.print_width, qr_size + 20), 1)
        offset_x = (self.print_width - qr_size) // 2
        canvas.paste(img, (offset_x, 10))

        tmp_path = '/tmp/paperang_qr.png'
        canvas.save(tmp_path)
        return self.print_image(tmp_path, heat_density=heat_density, vertical=vertical)

    def print_pickup_code(self, code, heat_density=100, compact=True,
                          vertical=False):
        """Print one or more pickup codes in large bold style (96px, centered).

        Args:
            code: Single code string, or list of code strings for
                  multiple codes on one printout.
            heat_density: Heat density 0-100 (default 100 for thermal paper).
            compact: Use tighter vertical spacing between multiple codes
                     (default True, ~30px gap; False uses ~60px gap).
            vertical: If True, rotate 90° clockwise for vertical printing.
        """
        codes = [code] if isinstance(code, str) else list(code)
        font_paths = self.font_paths_pickup or self._resolve_font_paths(BUNDLED_FONTS_PICKUP)
        font = self._load_font(font_paths, 96)

        # Measure the widest code for centering
        max_width = 0
        code_heights = []
        for c in codes:
            bbox = font.getbbox(c)
            w = bbox[2] - bbox[0] if bbox else 400
            h = bbox[3] - bbox[1] if bbox else 120
            max_width = max(max_width, w)
            code_heights.append(h)

        canvas_width = self.print_width
        line_spacing = 30 if compact else 60
        total_height = sum(code_heights) + len(codes) * line_spacing + 40
        canvas_height = ((total_height + 7) // 8) * 8
        canvas = Image.new('1', (canvas_width, canvas_height), 1)
        draw = ImageDraw.Draw(canvas)

        for i, c in enumerate(codes):
            bbox = font.getbbox(c)
            text_width = bbox[2] - bbox[0] if bbox else 400
            x = (canvas_width - text_width) // 2
            y = 20 + i * (code_heights[i] + line_spacing)
            draw.text((x, y), c, font=font, fill=0)

        tmp_path = '/tmp/paperang_pickup_code.png'
        canvas.save(tmp_path)
        return self.print_image(tmp_path, heat_density=heat_density,
                                feed_before=50, feed_after=200, vertical=vertical)

    # ── Test functions ──────────────────────────────────────────

    def print_pattern_test(self):
        """Print pattern test (line/column/multi-packet)."""
        width_bytes = self.line_bytes
        data = bytearray()

        # Test line length - 8 evenly sized column blocks.  Splitting the row
        # width (rather than a fixed 9 bytes) keeps this valid for every model:
        # 72 bytes -> 9-byte blocks, 48 bytes -> 6-byte blocks.
        columns = 8
        block_bytes = width_bytes // columns
        for _ in range(50):
            row = bytearray(width_bytes)
            for col in range(columns):
                start_byte = col * block_bytes
                for b in range(block_bytes):
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
        self.set_heat_density(DEFAULT_HEAT_DENSITY)
        self.feed(DEFAULT_FEED_BEFORE)
        self.print_bitmap(bytes(data), width_bytes)
        self.feed(DEFAULT_FEED_AFTER)
        return True

    def print_heat_density_test(self):
        """Print heat density test (0, 25, 50, 75, 100)."""
        width_bytes = self.line_bytes

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

        self.set_heat_density(DEFAULT_HEAT_DENSITY)
        self.feed(DEFAULT_FEED_AFTER)
        return True

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _load_font(font_paths, size):
        """Load first available font, fallback to default."""
        for fp in font_paths:
            if os.path.exists(fp):
                return ImageFont.truetype(fp, size)
        return ImageFont.load_default()
