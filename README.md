# paperang-p2-lib

[![PyPI - Version](https://img.shields.io/pypi/v/paperang-p2-lib.svg?style=flat-square)](https://pypi.org/project/paperang-p2-lib/)
[![Python Versions](https://img.shields.io/pypi/pyversions/paperang-p2-lib.svg?style=flat-square)](https://pypi.org/project/paperang-p2-lib/)
[![CI](https://github.com/mdj2812/paperang-p2-lib/actions/workflows/ci.yml/badge.svg)](https://github.com/mdj2812/paperang-p2-lib/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

Python library for Paperang P2 thermal printer (USB protocol).

Based on [hurui200320/java-paperang-p2-usb](https://github.com/hurui200320/java-paperang-p2-usb) protocol.

## Features

- USB connection to Paperang P2 printer
- Text printing (CJK support via optional `[cjk]` extra)
- Image printing with adjustable brightness/contrast/threshold
- QR code generation and printing
- Pickup code printing (large bold)
- Print profiles (portrait, landscape, document, etc.)
- Pattern test and heat density test
- Status and battery reading

## Installation

```bash
# Basic (Latin fonts only)
pip install paperang-p2-lib

# With QR code support
pip install paperang-p2-lib[qr]

# With CJK (Chinese/Japanese/Korean) text support
pip install paperang-p2-lib[cjk]

# All extras
pip install paperang-p2-lib[qr,cjk]
```

## Usage

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

# Get status
status = printer.get_status()
battery = printer.get_battery()
```

## API Reference

### `PaperangP2` Class

| Method | Description |
|--------|-------------|
| `connect()` | Connect to printer via USB |
| `print_text(text, font_size, heat_density)` | Print text (CJK requires `[cjk]` extra) |
| `print_image(path, heat_density, feed_before, feed_after, threshold, brightness, contrast)` | Print image |
| `print_qr(content, box_size, heat_density, max_width)` | Print QR code |
| `print_pickup_code(code, heat_density)` | Print large bold pickup code |
| `set_heat_density(density)` | Set heat density (0-100) |
| `set_paper_type(paper_type)` | Set paper type (0=normal, 1=continuous) |
| `feed(lines)` | Feed paper |
| `print_test_page()` | Print test page |
| `get_status()` | Get printer status |
| `get_battery()` | Get battery level |
| `print_pattern_test()` | Print pattern test |
| `print_heat_density_test()` | Print heat density gradient |

### Utility Functions

- `crc32_paperang(data, seed)` — Paperang-specific CRC32
- `pack_packet(cmd, data, packet_remain)` — Pack protocol packet
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

### Key Commands

| Command | Description |
|---------|-------------|
| 0x00 | Print bitmap data |
| 0x0C | Get status |
| 0x10 | Get battery level |
| 0x19 | Set heat density (0-100) |
| 0x1A | Feed paper |
| 0x1B | Print test page |
| 0x2C | Set paper type |

### CRC32

Custom seed `0x35769521` (standard CRC32 uses `0x00000000`).

## Related Projects

- [paperang-p2-usb](https://github.com/mdj2812/paperang-p2-usb) — CLI + MQTT wrapper
- [paperang-p2-fonts-cjk](https://github.com/mdj2812/paperang-p2-fonts-cjk) — CJK font package
- [paperang-hacs](https://github.com/mdj2812/paperang-hacs) — Home Assistant integration (HACS)

## License

MIT
