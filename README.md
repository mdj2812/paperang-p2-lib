# paperang-p2-lib

[![PyPI - Version](https://img.shields.io/pypi/v/paperang-p2-lib.svg?style=flat-square)](https://pypi.org/project/paperang-p2-lib/)
[![Python Versions](https://img.shields.io/pypi/pyversions/paperang-p2-lib.svg?style=flat-square)](https://pypi.org/project/paperang-p2-lib/)
[![CI](https://github.com/mdj2812/paperang-p2-lib/actions/workflows/ci.yml/badge.svg)](https://github.com/mdj2812/paperang-p2-lib/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

Python library for Paperang P2 thermal printer (USB + Bluetooth BLE).

Based on [hurui200320/java-paperang-p2-usb](https://github.com/hurui200320/java-paperang-p2-usb) protocol.

## Features

- USB and Bluetooth BLE connection to Paperang P2 printer
- Text printing (CJK support via optional `[cjk]` extra)
- Image printing with adjustable brightness/contrast/threshold
- QR code generation and printing
- Pickup code printing (large bold)
- Print profiles (portrait, landscape, document, etc.)
- Pattern test and heat density test
- Full protocol command coverage (48 commands)
- Status, battery, voltage, temperature reading

## Installation

```bash
# Basic (Latin fonts only, USB only)
pip install paperang-p2-lib

# With QR code support
pip install paperang-p2-lib[qr]

# With CJK (Chinese/Japanese/Korean) text support
pip install paperang-p2-lib[cjk]

# With Bluetooth BLE support
pip install paperang-p2-lib[ble]

# All extras
pip install paperang-p2-lib[qr,cjk,ble]
```

## Usage

### USB

```python
from paperang import PaperangP2

printer = PaperangP2()
printer.connect()

# Print text
printer.print_text("Hello World!", font_size=24)

# Print CJK text (requires [cjk] extra)
printer.print_text("你好世界", font_size=24)

# Print image
printer.print_image("photo.jpg", profile="portrait")

# Print QR code
printer.print_qr("https://example.com")

# Print pickup code
printer.print_pickup_code("19-4308")

# Read printer info
status  = printer.get_status()
battery = printer.get_battery()
voltage = printer.get_voltage()
temp    = printer.get_temperature()
version = printer.get_version()
model   = printer.get_model()
```

### Bluetooth BLE

```python
from paperang.transport import BleTransport
from paperang import PaperangP2

ble = BleTransport()                    # auto-scan for Paperang device
# ble = BleTransport(address="AA:BB:CC:DD:EE:FF")  # or specify MAC

printer = PaperangP2(transport=ble)
printer.connect()

# All print methods work the same way
printer.print_text("Hello from BLE!")
printer.get_battery()
```

#### Scan for nearby BLE devices

```bash
python -m tools.ble_scan
```

## API Reference

### Transport Classes

| Class | Description |
|-------|-------------|
| `Transport` (ABC) | Abstract transport interface |
| `UsbTransport` | USB transport (default when no transport is passed) |
| `BleTransport` | Bluetooth BLE transport (requires `[ble]` extra) |

### `PaperangP2` Class (high-level)

Inherits from `PaperangPrinter`. Adds image/text/QR rendering on top of low-level commands.

| Method | Description |
|--------|-------------|
| `connect()` | Connect to printer (default: USB; pass `transport=BleTransport()` for BLE) |
| `print_text(text, font_size, heat_density)` | Print text (CJK requires `[cjk]` extra) |
| `print_image(path, heat_density, feed_before, feed_after, threshold, brightness, contrast)` | Print image |
| `print_qr(content, box_size, heat_density, max_width)` | Print QR code |
| `print_pickup_code(code, heat_density)` | Print large bold pickup code |
| `print_pattern_test()` | Print pattern test |
| `print_heat_density_test()` | Print heat density gradient |

### `PaperangPrinter` Class (low-level)

| Method | Description |
|--------|-------------|
| `connect()` | Connect to printer via USB |
| `send(cmd, data)` | Send a single command packet |
| `send_multi_packet(cmd, data)` | Send data across multiple packets |
| `read_response(timeout)` | Read and parse printer response |
| `print_bitmap(data, width_bytes)` | Print raw bitmap data |
| `feed(lines)` | Feed paper |
| `feed_to_head(lines)` | Feed paper to print head position |
| `set_heat_density(density)` | Set heat density (0-100) |
| `set_paper_type(type)` | Set paper type (0=normal, 1=continuous) |
| `set_power_down_time(seconds)` | Set auto power-down time |
| `set_max_gap(gap)` | Set max gap length |
| `set_crc_key(key)` | Set CRC key |
| `set_factory_mode(mode)` | Set factory status |
| `print_test_page()` | Print test page |
| `print_default_para()` | Print default parameters page |
| `disconnect_bt()` | Disconnect Bluetooth |

### GET Methods

| Method | Command | Returns |
|--------|---------|---------|
| `get_status()` | 0x0C | Status hex string |
| `get_battery()` | 0x10 | Battery level (int) |
| `get_voltage()` | 0x0E | Voltage in mV (int) |
| `get_temperature()` | 0x12 | Temperature (int) |
| `get_heat_density()` | 0x1C | Heat density (int) |
| `get_power_down_time()` | 0x1F | Auto power-down seconds (int) |
| `get_paper_type()` | 0x2A | Paper type (int) |
| `get_max_gap()` | 0x28 | Max gap length (int) |
| `get_country()` | 0x2D | Country name (str) |
| `get_version()` | 0x04 | Firmware version (str) |
| `get_model()` | 0x06 | Printer model (str) |
| `get_bt_mac()` | 0x08 | Bluetooth MAC (hex str) |
| `get_sn()` | 0x0A | Serial number (str) |
| `get_board_version()` | 0x23 | Board version (str) |
| `get_hw_info()` | 0x25 | Hardware info (hex str) |
| `get_factory_status()` | 0x15 | Factory status (hex str) |

### Module Structure

```
paperang/
├── transport/          — Physical layer abstraction
│   ├── _base.py        — Transport ABC
│   ├── _usb.py         — UsbTransport (USB HID)
│   └── _ble.py         — BleTransport (Bluetooth BLE)
├── protocol/           — CRC, pack/unpack, 48 command constants (CMD_*)
├── printer/            — Printer / application layer
│   ├── _base.py        — PaperangPrinter (low-level commands)
│   ├── _printing.py    — PaperangP2 (high-level: image/text/QR rendering)
│   └── profiles.py     — load_profiles(), list_profiles()
├── constants.py        — USB IDs, dimensions, defaults, font paths
└── core.py             — Compatibility re-exports
```

### Utility Functions

- `crc32_paperang(data, seed)` — Paperang-specific CRC32
- `pack_packet(cmd, data, packet_remain)` — Pack protocol packet
- `unpack_response(raw_bytes)` — Parse a response frame
- `load_profiles(profiles_path)` — Load print profiles from JSON
- `list_profiles(profiles_path)` — Print available profiles

## Fonts

| Font | Size | Package | Purpose |
|------|------|---------|---------|
| DejaVuSans | 742K | ✅ Always included | Latin text fallback |
| DejaVuSans-Bold | 693K | ✅ Always included | Pickup codes (bold) |
| wqy-microhei | 5.0M | `[cjk]` extra | CJK (Chinese/Japanese/Korean) |

### CJK Support

CJK text printing requires the optional `[cjk]` dependency:

```bash
pip install paperang-p2-lib[cjk]
```

This installs [paperang-p2-fonts-cjk](https://github.com/mdj2812/paperang-p2-fonts-cjk),
which provides the 文泉驿微米黑 (WenQuanYi Micro Hei) font.

When `[cjk]` is installed, `print_text()` automatically uses the CJK font first,
falling back to DejaVuSans for Latin characters. Without `[cjk]`, CJK characters
will render as boxes or missing glyph symbols.

## Protocol Details

- **Vendor ID:** 0x4348
- **Product ID:** 0x5584
- **Print width:** 576 pixels (72 bytes/line)
- **Packet size:** 14 lines per packet (1008 bytes)

### Packet Format

```
[0x02] [CMD:1B] [packetRemain:1B] [dataLength:2B LE] [DATA:0-1023B] [CRC32:4B LE] [0x03]
```

### All Commands

| Hex | Constant | Description |
|-----|----------|-------------|
| 0x00 | `CMD_PRINT_BITMAP` | Print bitmap data |
| 0x01 | `CMD_PRINT_BITMAP_COMPRESS` | Print compressed bitmap |
| 0x02 | `CMD_FIRMWARE_DATA` | Firmware data transfer |
| 0x03 | `CMD_USB_UPDATE_FIRMWARE` | USB firmware update |
| 0x04 | `CMD_GET_VERSION` | Get firmware version |
| 0x06 | `CMD_GET_MODEL` | Get printer model |
| 0x08 | `CMD_GET_BT_MAC` | Get Bluetooth MAC |
| 0x0A | `CMD_GET_SN` | Get serial number |
| 0x0C | `CMD_GET_STATUS` | Get printer status |
| 0x0E | `CMD_GET_VOLTAGE` | Get battery voltage |
| 0x10 | `CMD_GET_BATTERY` | Get battery level |
| 0x12 | `CMD_GET_TEMP` | Get temperature |
| 0x14 | `CMD_SET_FACTORY` | Set factory status |
| 0x15 | `CMD_GET_FACTORY` | Get factory status |
| 0x17 | `CMD_SENT_BT_STATUS` | Set Bluetooth status |
| 0x18 | `CMD_SET_CRC_KEY` | Set CRC key |
| 0x19 | `CMD_SET_HEAT` | Set heat density |
| 0x1A | `CMD_FEED_PAPER` | Feed paper |
| 0x1B | `CMD_PRINT_TEST` | Print test page |
| 0x1C | `CMD_GET_HEAT` | Get heat density |
| 0x1E | `CMD_SET_POWER_DOWN` | Set power-down time |
| 0x1F | `CMD_GET_POWER_DOWN` | Get power-down time |
| 0x21 | `CMD_FEED_TO_HEAD` | Feed to print head |
| 0x22 | `CMD_PRINT_DEFAULT_PARA` | Print default params |
| 0x23 | `CMD_GET_BOARD_VERSION` | Get board version |
| 0x25 | `CMD_GET_HW_INFO` | Get hardware info |
| 0x27 | `CMD_SET_MAX_GAP` | Set max gap length |
| 0x28 | `CMD_GET_MAX_GAP` | Get max gap length |
| 0x2A | `CMD_GET_PAPER_TYPE` | Get paper type |
| 0x2C | `CMD_SET_PAPER` | Set paper type |
| 0x2D | `CMD_GET_COUNTRY` | Get country name |
| 0x2F | `CMD_DISCONNECT_BT` | Disconnect Bluetooth |

### CRC32

Custom seed `0x35769521` (standard CRC32 uses `0x00000000`).

### Dependencies

| Extra | Package | Purpose |
|-------|---------|---------|
| (always) | `pyusb>=1.2.1` | USB HID communication |
| (always) | `Pillow>=10.0.0` | Image processing |
| `[qr]` | `qrcode[pil]>=7.4.2` | QR code generation |
| `[cjk]` | `paperang-p2-fonts-cjk>=0.1.0` | CJK font (文泉驿微米黑) |
| `[ble]` | `bleak>=0.22.0` | Bluetooth BLE (cross-platform) |

## Related Projects

- [paperang-p2-usb](https://github.com/mdj2812/paperang-p2-usb) — CLI + MQTT wrapper
- [paperang-p2-fonts-cjk](https://github.com/mdj2812/paperang-p2-fonts-cjk) — CJK font package
- [paperang-hacs](https://github.com/mdj2812/paperang-hacs) — Home Assistant integration (HACS)

## License

MIT
