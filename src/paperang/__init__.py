"""Paperang P2 USB Printer Library."""

from .constants import (
    VENDOR_ID,
    PRODUCT_ID,
    PRINT_WIDTH,
    LINE_BYTES,
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
from .protocol import (
    CRC_SEED,
    MAX_PACKET_DATA,
    crc32_paperang,
    pack_packet,
    unpack_response,
    CMD_PRINT_BITMAP,
    CMD_GET_STATUS,
    CMD_GET_BATTERY,
    CMD_PRINT_TEST,
    CMD_SET_HEAT,
    CMD_FEED_PAPER,
    CMD_SET_PAPER,
)
from .core import PaperangP2
from .profiles import load_profiles, list_profiles

__all__ = [
    # Constants
    "VENDOR_ID", "PRODUCT_ID", "PRINT_WIDTH", "LINE_BYTES",
    "PAPER_TYPE_NORMAL", "PAPER_TYPE_CONTINUOUS",
    "DEFAULT_HEAT_DENSITY", "DEFAULT_THRESHOLD",
    "DEFAULT_BRIGHTNESS", "DEFAULT_CONTRAST", "DEFAULT_FONT_SIZE",
    "DEFAULT_FEED_BEFORE", "DEFAULT_FEED_AFTER",
    "BUNDLED_FONTS_TEXT", "BUNDLED_FONTS_PICKUP", "BUNDLED_FONTS_CJK",
    # Protocol
    "CRC_SEED", "MAX_PACKET_DATA",
    "crc32_paperang", "pack_packet", "unpack_response",
    "CMD_PRINT_BITMAP", "CMD_GET_STATUS", "CMD_GET_BATTERY",
    "CMD_PRINT_TEST", "CMD_SET_HEAT", "CMD_FEED_PAPER", "CMD_SET_PAPER",
    # Core
    "PaperangP2",
    # Profiles
    "load_profiles", "list_profiles",
]
