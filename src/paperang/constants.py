"""Constants for Paperang printers.

The module-level values describe the Paperang P2 and are kept for backward
compatibility.  They are derived from the built-in P2
:class:`~paperang.models.PrinterModel`; for other models use
:func:`paperang.get_model` and read the attributes off the returned model.
"""

import os

from .models import DEFAULT_MODEL, get_model

_P2 = get_model(DEFAULT_MODEL)

# USB IDs (Paperang P2)
VENDOR_ID = _P2.vid
PRODUCT_ID = _P2.pid

# Physical print parameters (Paperang P2)
PRINT_WIDTH = _P2.print_width   # pixels (72 bytes/line * 8)
LINE_BYTES = _P2.line_bytes     # bytes per line

# Paper types
PAPER_TYPE_NORMAL = 0
PAPER_TYPE_CONTINUOUS = 1

# Default print settings.  These are job-level values, not model properties:
# a print profile (load_profiles()) or an explicit call argument overrides them.
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
