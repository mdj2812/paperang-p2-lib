"""Paperang P2 USB Printer Library.

Modules:
    protocol   — CRC, packet pack/unpack, command codes
    printer    — USB connection, low-level send/read, basic commands
    printing   — Image/text/QR rendering, high-level print functions
    profiles   — Print profile management
    constants  — USB IDs, dimensions, defaults, font paths
"""

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
    # Command codes (all from Paperang protocol spec)
    CMD_PRINT_BITMAP,
    CMD_PRINT_BITMAP_COMPRESS,
    CMD_FIRMWARE_DATA,
    CMD_USB_UPDATE_FIRMWARE,
    CMD_GET_VERSION,
    CMD_GET_MODEL,
    CMD_GET_BT_MAC,
    CMD_GET_SN,
    CMD_GET_STATUS,
    CMD_GET_VOLTAGE,
    CMD_GET_BATTERY,
    CMD_GET_TEMP,
    CMD_GET_HEAT,
    CMD_GET_POWER_DOWN,
    CMD_GET_BOARD_VERSION,
    CMD_GET_HW_INFO,
    CMD_GET_MAX_GAP,
    CMD_GET_PAPER_TYPE,
    CMD_GET_COUNTRY,
    CMD_GET_FACTORY,
    CMD_SET_HEAT,
    CMD_SET_PAPER,
    CMD_SET_FACTORY,
    CMD_SET_CRC_KEY,
    CMD_SET_POWER_DOWN,
    CMD_SET_MAX_GAP,
    CMD_FEED_PAPER,
    CMD_FEED_TO_HEAD,
    CMD_PRINT_TEST,
    CMD_PRINT_DEFAULT_PARA,
    CMD_DISCONNECT_BT,
)
from .printer import PaperangPrinter
from .printing import PaperangP2
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
    "CMD_PRINT_BITMAP", "CMD_PRINT_BITMAP_COMPRESS",
    "CMD_FIRMWARE_DATA", "CMD_USB_UPDATE_FIRMWARE",
    "CMD_GET_VERSION", "CMD_GET_MODEL", "CMD_GET_BT_MAC", "CMD_GET_SN",
    "CMD_GET_STATUS", "CMD_GET_VOLTAGE", "CMD_GET_BATTERY", "CMD_GET_TEMP",
    "CMD_GET_HEAT", "CMD_GET_POWER_DOWN", "CMD_GET_BOARD_VERSION",
    "CMD_GET_HW_INFO", "CMD_GET_MAX_GAP", "CMD_GET_PAPER_TYPE",
    "CMD_GET_COUNTRY", "CMD_GET_FACTORY",
    "CMD_SET_HEAT", "CMD_SET_PAPER", "CMD_SET_FACTORY", "CMD_SET_CRC_KEY",
    "CMD_SET_POWER_DOWN", "CMD_SET_MAX_GAP",
    "CMD_FEED_PAPER", "CMD_FEED_TO_HEAD",
    "CMD_PRINT_TEST", "CMD_PRINT_DEFAULT_PARA",
    "CMD_DISCONNECT_BT",
    # Classes
    "PaperangPrinter", "PaperangP2",
    # Profiles
    "load_profiles", "list_profiles",
]
