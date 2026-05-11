"""Paperang P2 USB Printer — Protocol layer.

Handles CRC calculation, packet encoding/decoding, and command constants
for the Paperang printer communication protocol.
"""

import struct
import zlib

# ── Protocol frame constants ────────────────────────────────────

FRAME_HEADER = 0x02
FRAME_FOOTER = 0x03
CRC_SEED = 0x35769521 & 0xFFFFFFFF
MAX_PACKET_DATA = 1023  # max data bytes per packet

# ── Command codes ───────────────────────────────────────────────

CMD_PRINT_BITMAP = 0x00
CMD_PRINT_BITMAP_COMPRESS = 0x01
CMD_FIRMWARE_DATA = 0x02
CMD_USB_UPDATE_FIRMWARE = 0x03
CMD_GET_VERSION = 0x04
CMD_SENT_VERSION = 0x05
CMD_GET_MODEL = 0x06
CMD_SENT_MODEL = 0x07
CMD_GET_BT_MAC = 0x08
CMD_SENT_BT_MAC = 0x09
CMD_GET_SN = 0x0A
CMD_SENT_SN = 0x0B
CMD_GET_STATUS = 0x0C
CMD_SENT_STATUS = 0x0D
CMD_GET_VOLTAGE = 0x0E
CMD_SENT_VOLTAGE = 0x0F
CMD_GET_BATTERY = 0x10
CMD_SENT_BAT_STATUS = 0x11
CMD_GET_TEMP = 0x12
CMD_SENT_TEMP = 0x13
CMD_SET_FACTORY = 0x14
CMD_GET_FACTORY = 0x15
CMD_SENT_FACTORY = 0x16
CMD_SENT_BT_STATUS = 0x17
CMD_SET_CRC_KEY = 0x18
CMD_SET_HEAT = 0x19
CMD_FEED_PAPER = 0x1A
CMD_PRINT_TEST = 0x1B
CMD_GET_HEAT = 0x1C
CMD_SENT_HEAT = 0x1D
CMD_SET_POWER_DOWN = 0x1E
CMD_GET_POWER_DOWN = 0x1F
CMD_SENT_POWER_DOWN = 0x20
CMD_FEED_TO_HEAD = 0x21
CMD_PRINT_DEFAULT_PARA = 0x22
CMD_GET_BOARD_VERSION = 0x23
CMD_SENT_BOARD_VERSION = 0x24
CMD_GET_HW_INFO = 0x25
CMD_SENT_HW_INFO = 0x26
CMD_SET_MAX_GAP = 0x27
CMD_GET_MAX_GAP = 0x28
CMD_SENT_MAX_GAP = 0x29
CMD_GET_PAPER_TYPE = 0x2A
CMD_SENT_PAPER_TYPE = 0x2B
CMD_SET_PAPER = 0x2C
CMD_GET_COUNTRY = 0x2D
CMD_SENT_COUNTRY = 0x2E
CMD_DISCONNECT_BT = 0x2F


def crc32_paperang(data, seed=CRC_SEED):
    """Paperang-specific CRC32 calculation.

    Uses seed = 0x35769521 (standard CRC32 uses 0x00000000).
    """
    crc = zlib.crc32(data, seed) & 0xFFFFFFFF
    if crc > 2147483647:
        crc -= 4294967296
    return crc


def pack_packet(cmd, data=b'', packet_remain=0):
    """Pack Paperang protocol packet.

    Format: [0x02] [CMD:1B] [packetRemain:1B] [dataLength:2B LE]
            [DATA:0-1023B] [CRC32:4B LE] [0x03]
    """
    crc = crc32_paperang(data)
    packet = bytearray()
    packet.append(FRAME_HEADER)                     # Packet header
    packet.append(cmd & 0xFF)                       # Command (1 byte)
    packet.append(packet_remain & 0xFF)             # Remaining packets (1 byte)
    packet.extend(struct.pack('<H', len(data)))     # Data length (2 bytes, LE)
    packet.extend(data)                             # Data (0-1023 bytes)
    packet.extend(struct.pack('<i', crc))           # CRC32 (4 bytes, LE, signed)
    packet.append(FRAME_FOOTER)                     # Packet footer
    return bytes(packet)


def unpack_response(raw_bytes):
    """Parse a response frame from raw bytes.

    Returns dict with ``cmd``, ``packet_remain``, ``data``, ``crc`` or ``None``
    if the frame is invalid or incomplete.
    """
    if len(raw_bytes) < 10:
        return None

    # Find frame header
    start_idx = 0
    for i in range(len(raw_bytes)):
        if raw_bytes[i] == FRAME_HEADER:
            start_idx = i
            break

    if start_idx + 10 > len(raw_bytes):
        return None

    cmd = raw_bytes[start_idx + 1]
    packet_remain = raw_bytes[start_idx + 2]
    data_len = struct.unpack('<H', raw_bytes[start_idx + 3:start_idx + 5])[0]

    if start_idx + 5 + data_len + 4 + 1 > len(raw_bytes):
        return None

    data = bytes(raw_bytes[start_idx + 5:start_idx + 5 + data_len])
    crc = struct.unpack('<I',
                        raw_bytes[start_idx + 5 + data_len:start_idx + 5 + data_len + 4])[0]
    end_byte = raw_bytes[start_idx + 5 + data_len + 4]

    if end_byte != FRAME_FOOTER:
        return None

    return {'cmd': cmd, 'packet_remain': packet_remain, 'data': data, 'crc': crc}
