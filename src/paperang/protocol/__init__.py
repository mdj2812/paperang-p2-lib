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
    """Parse all response frames from raw bytes.

    GET commands receive two frames in a single response:
    1. Echo of the original command
    2. Actual data with a different response code

    Returns a list of dicts, each with ``cmd``, ``packet_remain``, ``data``, ``crc``.
    Returns empty list if no valid frames found.
    """
    frames = []
    offset = 0
    buf = raw_bytes if isinstance(raw_bytes, (bytes, bytearray)) else bytes(raw_bytes)

    while offset < len(buf) - 9:  # minimum frame: 1+1+1+2+0+4+1 = 10
        # Find frame header
        header_idx = buf.find(bytes([FRAME_HEADER]), offset)
        if header_idx < 0:
            break

        if header_idx + 10 > len(buf):
            break

        cmd = buf[header_idx + 1]
        packet_remain = buf[header_idx + 2]
        data_len = struct.unpack('<H', buf[header_idx + 3:header_idx + 5])[0]

        frame_end = header_idx + 5 + data_len + 4 + 1  # header + cmd + remain + len + data + crc + footer
        if frame_end > len(buf):
            break

        data = bytes(buf[header_idx + 5:header_idx + 5 + data_len])
        crc = struct.unpack('<I',
                            buf[header_idx + 5 + data_len:header_idx + 5 + data_len + 4])[0]
        end_byte = buf[header_idx + 5 + data_len + 4]

        if end_byte != FRAME_FOOTER:
            offset = header_idx + 1
            continue

        frames.append({'cmd': cmd, 'packet_remain': packet_remain, 'data': data, 'crc': crc})
        offset = frame_end

    return frames
