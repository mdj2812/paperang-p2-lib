<!--
Pull request template for adding a printer model.

Open it directly with:
https://github.com/mdj2812/paperang-p2-lib/compare/main...YOUR-BRANCH?template=adding_a_model.md&expand=1

Full guide: docs/adding-a-model.md
-->

## Model

- Model name:
- Bluetooth name:
- `CMD_GET_MODEL` returns:
- USB VID:PID: `0x…:0x…`
- Print head width: … dots (… bytes/row)
- Paper / format:

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
