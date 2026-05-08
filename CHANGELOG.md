# Changelog

All notable changes to this project will be documented in this file.

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
