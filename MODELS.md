# Supported models

Paperang printers share one protocol — command set, CRC and packet framing — so
what differs between models is identity and print-head geometry. That data lives
in one JSON file per model under
[`src/paperang/models/`](src/paperang/models/).

| Model | USB PID | Print head | Transports | Status |
|-------|---------|------------|------------|--------|
| P2 | `0x5584` | 576 dots (72 bytes/row) | USB, Bluetooth SPP | Verified |
| D1 / ZYB-D1 | `0x5585` | 384 dots (48 bytes/row) | USB, Bluetooth SPP | Verified (community report) |

All models share the Paperang vendor ID `0x4348`.

## How a device is identified

`Paperang.auto_detect()` connects first and identifies the printer afterwards:

- **USB**: every registered product ID is tried in one pass, then the model is
  confirmed against the string reported by `CMD_GET_MODEL`.
- **Classic Bluetooth**: discovery and RFCOMM channel probing are model-agnostic,
  because Bluetooth carries no VID/PID. The model is read from `CMD_GET_MODEL`
  once the link is up, so an unregistered model can still connect and say what
  it is.
- When the USB ID and the reported name disagree, the reported name wins and a
  warning is logged — that normally means the model table is out of date.
- When neither matches, `UnknownModelError` names the device, lists the known
  models, and explains how to pass a model explicitly.

Passing a path to a model file (`Paperang(model="./my-model.json")`) works
without registering anything, which is how a new model can be tried before it is
contributed.

## What the status means

- **P2** — verified. Covered by the test suite and used in production by the
  [Home Assistant integration](https://github.com/mdj2812/paperang-hacs).
- **D1 / ZYB-D1** — verified by a community report
  ([#22](https://github.com/mdj2812/paperang-p2-lib/issues/22)): USB printing
  and the 384-dot layout were confirmed, and classic Bluetooth SPP prints as
  well, on RFCOMM channel 1.

  Known hardware behaviour to be aware of:

  - it does **not** answer `CMD_GET_MODEL` or `CMD_GET_STATUS`, so it cannot be
    identified by name over Bluetooth — pass `model="d1"` there
  - it hangs when `CMD_SET_PAPER` is sent, so `supports_set_paper_type` is
    `false` and the print paths skip that command
  - the official app's print darkness is reached around `heat_density=100`,
    rather than the default 75

## Adding a model

Adding a model is adding a JSON file. See
[docs/adding-a-model.md](docs/adding-a-model.md) for the field reference, the
hardware checks, and the pull request template.

Two rules matter most:

- **The device must speak the same protocol.** A matching print-head width is not
  enough — there are 384-dot Bluetooth thermal printers that this library cannot
  drive at all.
- **The `CMD_GET_MODEL` spelling must be listed in `aliases`**, otherwise a
  connected printer cannot be resolved to its model.

## Transports

USB and classic Bluetooth SPP (RFCOMM) only. BLE is out of scope.
