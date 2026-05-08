"""Constants for Paperang P2 Printer."""

# USB IDs
VENDOR_ID = 0x4348
PRODUCT_ID = 0x5584

# Protocol
CRC_SEED = 0x35769521 & 0xFFFFFFFF
PRINT_WIDTH = 576  # pixels (72 bytes/line * 8)
LINE_BYTES = 72    # bytes per line
MAX_PACKET_DATA = 1023  # max data bytes per packet

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

# Font files (relative to package directory)
BUNDLED_FONTS_TEXT = [
    "fonts/wqy-microhei.ttc",  # CJK support
    "fonts/DejaVuSans.ttf",    # Latin fallback
]
BUNDLED_FONTS_PICKUP = [
    "fonts/DejaVuSans-Bold.ttf",
    "fonts/DejaVuSans.ttf",
]
