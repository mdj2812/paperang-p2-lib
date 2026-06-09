# Changelog

## [1.1.2] - 2026-06-09

### Removed
- **BLE transport (`BleTransport`)** — removed entirely. The Paperang P2 uses
  BR/EDR (classic Bluetooth SPP), not BLE. Use `BtTransport` for wireless.
- `[ble]` extra (`bleak>=0.22.0`) from `pyproject.toml`
- `tools/ble_scan.py` — BLE device scanner
- `tests/test_ble.py` — 319 lines of BLE-only tests removed (now covered
  via `BtTransport`)
- NUS (Nordic UART Service) UUID constants from `constants.py`

### Changed
- README: replace BLE examples with `BtTransport` (Bluetooth SPP)

## [1.1.1] - 2026-06-09

### Fixed
- `BtTransport.recv()` now restores the socket timeout after reading.
  Previously it changed the timeout to 1 s (read timeout) without restoring
  the original connection timeout, causing `sendall()` in `print_bitmap()`
  to time out on large transmissions.

## [1.1.0] - 2026-06-08

### Added
- `BtTransport` — classic Bluetooth SPP (RFCOMM) support via Linux
  `AF_BLUETOOTH` sockets.  Zero extra Python dependencies.

## [1.0.0] - 2026-06-07

### Changed
- **Stable release** — promoted from Alpha to Production/Stable
- BLE `recv()` upgraded from polling loop to `asyncio.Queue` for proper
  non-busy-wait RX handling

### Fixed
- `get_heat_density()` now handles single-byte P2 responses (device returns
  1 byte, 0-100, not 2 bytes LE)
- `_send_get()` retries reads up to 3 times with 100 ms delay to handle
  P2 buffered/stale response frames

### Added
- `_drain()` utility method for clearing stale data from the USB IN endpoint

## [0.4.0rc1] - 2026-05-13

### Added
- `BleTransport` — Bluetooth Low Energy transport via Nordic UART Service (NUS)
- Optional `[ble]` extra (`bleak>=0.22.0`) for cross-platform BLE support
- `tools/ble_scan.py` — CLI BLE device scanner
- BLE device auto-discovery: scans for `Paperang` and `MiaoMiaoJi` (喵喵机) names
- NUS UUID constants (`NUS_SERVICE_UUID`, `NUS_TX_UUID`, `NUS_RX_UUID`) in `constants.py`
- 22 mock-based BLE transport tests (constructor, send/recv, connect, callbacks)

## [0.3.7] - 2026-05-13

### Changed
- Refactored physical transport layer behind `Transport` abstract base class;
  `UsbTransport` moved to `_usb.py` for cleaner separation
- Reorganized package into `transport/` / `protocol/` / `printer/` subpackages
  (internal structure only; public API unchanged)
- Migrated printer module files: `printer.py` → `printer/_base.py`,
  `printing.py` → `printer/_printing.py`

### Added
- CI test coverage reporting with 85% minimum threshold
- GitHub-native coverage badge via shields.io
- 70+ mock-based tests for printer layer, USB transport, and profiles
- Tests split into transport / protocol / printer layers

## [0.3.6] - 2026-05-12

### Fixed
- `print_image()` now supports remote URLs (http/https) by downloading them
  before opening, in addition to local file paths


## [0.3.5] - 2026-05-12

### Fixed
- `get_version()` now detects binary firmware version data (e.g. `\x00\x01`)
  and converts it to an integer string instead of decoding as UTF-8 garbage


All notable changes to this project will be documented in this file.

## [0.3.4] - 2026-05-12

### Fixed
- String decoding helpers (`get_version`, `get_model`, `get_sn`, `get_board_version`)
  now strip NUL bytes and whitespace before decoding, preventing "\ufffd"
  replacement-character garbage in firmwware version/model/serial strings
- Added `_clean_str()` static method for consistent bytes→string cleanup

## [0.3.3] - 2026-05-12

### Fixed
- `_send_get()` now matches response frame by `cmd + 1` (e.g., GET_STATUS 0x0C → SENT_STATUS 0x0D)
  instead of simply skipping the echo frame

## [0.3.2] - 2026-05-12

### Fixed
- `unpack_response()` now parses multiple frames from a single USB response
- `_send_get()` correctly finds the non-echo frame when printer sends command echo + data together
- `read_response()` returns list of frame dicts (empty list on error)

## [0.3.1] - 2026-05-12

### Fixed
- `_send_get()` now correctly handles dual-response protocol: discards first
  response (command echo) and returns data from second response (e.g., battery
  level from CMD_SENT_BAT_STATUS = 0x11)

## [0.3.0] - 2026-05-12

### Added
- All 48 protocol command codes exported as constants (`CMD_*`)
- 16 new `get_*` methods: voltage, temperature, heat_density, power_down_time,
  paper_type, max_gap, country, version, model, bt_mac, sn, board_version,
  hw_info, factory_status
- 5 new `set_*` methods: power_down_time, max_gap, crc_key, factory_mode
- New methods: `feed_to_head()`, `print_default_para()`, `disconnect_bt()`
- `_send_get()` helper for all GET commands (sends `struct.pack('<B', 1)`)

### Fixed
- `get_status()` and `get_battery()` now send required data byte

## [0.2.2] - 2026-05-12

### Fixed
- `get_status()` and `get_battery()` now send required data byte `struct.pack('<B', 1)`

## [0.2.1] - 2026-05-11

### Changed
- Module restructure: protocol, printer, printing, profiles separated from core
- `protocol.py`: CRC, pack/unpack, command codes
- `printer.py`: USB connection, low-level commands (`PaperangPrinter` class)
- `printing.py`: image/text/QR rendering (`PaperangP2` extends `PaperangPrinter`)
- `profiles.py`: print profile management
- `constants.py` slimmed to USB IDs, print params, defaults, font paths
- `core.py` now a thin compat re-export layer
- Added `unpack_response()` for parsing printer response frames
- Tests updated for new structure; +8 new tests (24 total)

## [0.2.0] - 2026-05-08

### Added
- `[cjk]` optional dependency for CJK (Chinese/Japanese/Korean) text support
- `paperang-p2-fonts-cjk` as an optional PyPI package with wqy-microhei font
- `tests/` directory with 16 unit tests (constants, fonts, protocol, CRC)
- CI `test-cjk` job to verify CJK font detection when `[cjk]` is installed
- CI `pytest` step to both test jobs

### Fixed
- Missing `import os` in `constants.py` (F821 lint error)
- CJK font detection using `importlib.resources` — now requires `__init__.py` in fonts-cjk package

### Changed
- CJK font is now optional via `[cjk]` extra (was misleadingly documented as "always included")
- README updated with proper installation instructions for `[cjk]` and `[qr]` extras
- `BUNDLED_FONTS_CJK` gracefully falls back to empty list when `[cjk]` is not installed

### Removed
- Bundled wqy-microhei.ttc from main package (now in separate `paperang-p2-fonts-cjk`)
