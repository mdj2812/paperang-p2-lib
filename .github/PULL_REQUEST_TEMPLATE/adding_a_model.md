<!--
Pull request template for adding a printer model.

Open it directly with:
https://github.com/mdj2812/paperang-p2-lib/compare/main...YOUR-BRANCH?template=adding_a_model.md&expand=1

Full guide: docs/adding-a-model.md
-->

## Model

<!-- Replace the examples: they show the P2, whose values are known good. If a
     value cannot be measured yet, write that instead of guessing. -->

- Model name: `P2` — also becomes the model file name, lower-cased (`p2.json`)
- Bluetooth name: `Paperang_P2` — exactly as `bluetoothctl devices` reports it
- `CMD_GET_MODEL` returns: `Paperang_P2` — what `printer.get_model()` prints
- USB VID:PID: `0x4348:0x5584` — from `lsusb`, or the HA config flow
- Print head width: 576 dots (72 bytes/row, i.e. dots ÷ 8) — confirm from a test print
- Paper / format: roll or label size you printed on, e.g. 57 mm continuous

## Protocol compatibility

<!-- A matching print-head width is not enough: the device must speak the same protocol. -->

- [ ] Prints after changing only the USB product ID and print width
- [ ] Reports a Paperang model string from `CMD_GET_MODEL`
- [ ] Read commands round-trip (`GET_STATUS`, `GET_BATTERY`, …)
- [ ] Not a third-party printer with a similar head width, and not BLE-only (#28)

## Model file

- [ ] Added `src/paperang/models/<name>.json`
- [ ] The `CMD_GET_MODEL` spelling is listed in `aliases`
- [ ] `print_width` was confirmed from a test print, not a datasheet
- [ ] `transports` lists only what was actually tested
- [ ] Added the model to the "Supported models" table in `README.md`
- [ ] `python -m pytest` passes

## Evidence

- [ ] `lsusb` output: `…`
- [ ] Photo of a test print attached
- [ ] `Paperang.auto_detect()` resolves the model

## Verification

| Transport | Tested | Notes |
|---|---|---|
| USB |  |  |
| Classic Bluetooth SPP |  |  |

## Notes

<!-- Anything unusual: feed distances, a vendor service UUID, a fixed RFCOMM
channel, output that clips, paper that is narrower than the head. -->
