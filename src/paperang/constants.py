"""Constants for Paperang P2 Printer."""

import os

# USB IDs
VENDOR_ID = 0x4348
PRODUCT_ID = 0x5584

# Physical print parameters
PRINT_WIDTH = 576  # pixels (72 bytes/line * 8)
LINE_BYTES = 72    # bytes per line

# Paper types
PAPER_TYPE_NORMAL = 0
PAPER_TYPE_CONTINUOUS = 1

# Default print settings
DEFAULT_HEAT_DENSITY = 75
DEFAULT_THRESHOLD = 128
DEFAULT_BRIGHTNESS = 1.0
DEFAULT_CONTRAST = 1.0
DEFAULT_FONT_SIZE = 24
DEFAULT_FEED_BEFORE = 50
DEFAULT_FEED_AFTER = 300

# Bundled font files (relative to package directory)
# Latin fonts — always included
BUNDLED_FONTS_TEXT = [
    "fonts/latin/DejaVuSans.ttf",
]
BUNDLED_FONTS_PICKUP = [
    "fonts/latin/DejaVuSans-Bold.ttf",
    "fonts/latin/DejaVuSans.ttf",
]

# CJK fonts — provided by paperang-p2-fonts-cjk (optional)
# When installed, fonts live in paperang_p2_fonts_cjk/fonts/
try:
    import importlib.resources
    _cjk_pkg = importlib.resources.files("paperang_p2_fonts_cjk")
    _cjk_fonts_path = str(_cjk_pkg / "fonts")
    BUNDLED_FONTS_CJK = [
        os.path.join(_cjk_fonts_path, "wqy-microhei.ttc"),
    ]
except ImportError:
    BUNDLED_FONTS_CJK = []
except Exception:
    BUNDLED_FONTS_CJK = []
