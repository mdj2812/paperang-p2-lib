"""Paperang P2 USB Printer Library."""

from .constants import (
    VENDOR_ID,
    PRODUCT_ID,
    CRC_SEED,
    PRINT_WIDTH,
    LINE_BYTES,
    MAX_PACKET_DATA,
    PAPER_TYPE_NORMAL,
    PAPER_TYPE_CONTINUOUS,
    DEFAULT_HEAT_DENSITY,
    DEFAULT_THRESHOLD,
    DEFAULT_BRIGHTNESS,
    DEFAULT_CONTRAST,
    DEFAULT_FONT_SIZE,
    DEFAULT_FEED_BEFORE,
    DEFAULT_FEED_AFTER,
    BUNDLED_FONTS_TEXT,
    BUNDLED_FONTS_PICKUP,
    BUNDLED_FONTS_CJK,
)
from .core import (
    crc32_paperang,
    pack_packet,
    PaperangP2,
    load_profiles,
    list_profiles,
)

__all__ = [
    # Constants
    "VENDOR_ID", "PRODUCT_ID", "CRC_SEED", "PRINT_WIDTH",
    "LINE_BYTES", "MAX_PACKET_DATA",
    "PAPER_TYPE_NORMAL", "PAPER_TYPE_CONTINUOUS",
    "DEFAULT_HEAT_DENSITY", "DEFAULT_THRESHOLD",
    "DEFAULT_BRIGHTNESS", "DEFAULT_CONTRAST", "DEFAULT_FONT_SIZE",
    "DEFAULT_FEED_BEFORE", "DEFAULT_FEED_AFTER",
    "BUNDLED_FONTS_TEXT", "BUNDLED_FONTS_PICKUP", "BUNDLED_FONTS_CJK",
    # Core
    "crc32_paperang", "pack_packet", "PaperangP2",
    "load_profiles", "list_profiles",
]
