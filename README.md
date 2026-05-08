# paperang-p2-lib

Python library for Paperang P2 thermal printer (USB protocol).

Based on [java-paperang-p2-usb](https://github.com/hurui200320/java-paperang-p2-usb) protocol.

## Features

- USB connection to Paperang P2 printer
- Text printing with CJK font support
- Image printing with adjustable brightness/contrast/threshold
- QR code generation and printing
- Pickup code printing (large bold)
- Print profiles (portrait, landscape, document, etc.)
- Pattern test and heat density test
- Status and battery reading

## Installation

```bash
pip install .

# With QR code support
pip install ".[qr]"
```

## Usage

```python
from paperang import PaperangP2

printer = PaperangP2()
printer.connect()

# Print text
printer.print_text("Hello World!", font_size=24)

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

## CLI (see paperang-p2-usb)

For command-line usage, see the [paperang-p2-usb](https://github.com/mdj2812/paperang-p2-usb) project.

## License

MIT
