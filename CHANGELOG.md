# Changelog

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
