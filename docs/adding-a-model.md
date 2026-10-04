# Adding a printer model

Paperang printers share one protocol. What differs between models is *identity*
(USB IDs, Bluetooth names) and *geometry* (print-head width), so adding a model
means adding a small JSON file — no Python changes.

## Model vs profile

- A **model** is the hardware: which device is connected and how wide its print
  head is. Models live in `src/paperang/models/<name>.json`.
- A **profile** is a print-quality preset — `threshold`, `brightness`,
  `contrast`, `heat_density` — stored in `src/paperang/profiles.json` and loaded
  by `load_profiles()`.

The two are kept apart on purpose: a model file that contains a print setting
such as `heat_density` is rejected with an `unknown field` error, so print
quality never gets baked into a hardware definition.

## Model fields

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Human-readable name, e.g. `"P2"`. |
| `vid` | yes | USB vendor ID, as `"0x4348"` or `17224`. |
| `pids` | yes | USB product IDs, most common first. |
| `print_width` | yes | Print-head width in dots; a positive multiple of 8. |
| `aliases` | no | Other spellings the device is known by. Include the exact string `CMD_GET_MODEL` returns — see the warning below. |
| `transports` | no | Which transports the model supports: `["usb"]`, `["spp"]`, or both. Defaults to both. |
| `bt_name_prefixes` | no | Bluetooth device-name prefixes used during discovery, lower-case. |
| `bt_service_uuids` | no | Vendor service UUIDs, in the canonical 128-bit form. |
| `bt_rfcomm_channel` | no | Known RFCOMM channel, for models where SDP probing cannot find one. |

Derived values are deliberately not stored: `line_bytes` comes from
`print_width`, and the protocol's per-packet row count comes from `line_bytes`.

**Warning — the alias must match `CMD_GET_MODEL`.** Model strings are matched
through the alias table, so a printer reporting `Paperang_D1` will not resolve
unless the model file lists that spelling:

```json
{
  "name": "D1",
  "vid": "0x4348",
  "pids": ["0x5585"],
  "print_width": 384,
  "aliases": ["paperang_d1", "zyb-d1"]
}
```

Matching ignores case and punctuation, so `paperang_d1`, `Paperang D1` and
`Paperang-D1` are the same alias.

## Admission criteria

A model belongs here if the **device speaks the same protocol** — not merely
because its print head has the same width:

- *In scope*: `ZYB-D1` (Bluetooth name `Paperang_D1`). It prints after changing
  only the USB product ID and print width, and it reports a Paperang model
  string, so it is the same protocol on a 384-dot head.
- *Out of scope*: Cuoti Xiaoyin X1 (错题小印 X1). It is also a 384-dot Bluetooth
  thermal printer, but it uses a different protocol and cannot be enabled by
  configuration.

BLE is out of scope as well: the library speaks USB and classic Bluetooth SPP
(RFCOMM) only. BLE-only models should be declined rather than half-supported.

## 1. Collect the device details

Please include all of these in the issue or pull request — they are what makes
the model entry verifiable:

- `lsusb` output while the printer is connected (or `0xVID:0xPID` from the
  config flow)
- Bluetooth device name, as reported by `bluetoothctl devices`
- the string returned by `CMD_GET_MODEL` — easiest via
  `Paperang(auto-detected)` or `printer.get_model()`
- a print of `printer.print_pattern_test()`, or any output showing the head
  width reaching the paper edge without clipping
- which transports you tested: USB, classic Bluetooth, or both

Take `print_width` from the confirmed print-out, not from a vendor datasheet.
Row width is not scalable: the bytes per row sent to the printer must equal
head dots / 8, and getting it wrong produces skewed or clipped output rather
than an error.

## 2. Try it without touching the library

Write the model file anywhere and pass the path to the printer:

```python
from paperang import Paperang

printer = Paperang(model="./my-model.json")
printer.connect()
printer.print_text("Hello from a new model")
```

Configurations loaded this way are not registered globally, so
`Paperang.auto_detect()` will not find them yet — that is what the pull request
below changes.

## 3. Submit it

1. Add `src/paperang/models/<name>.json`.
2. Add the model to the "Supported models" table in `README.md`.
3. Run the test suite — the geometry and model-loading tests are parameterized
   over the model table, so a new file is covered automatically:

   ```bash
   python -m pytest
   ```

4. Open a pull request referencing the model issue, with the collected evidence
   and, ideally, a photo of the test print. There is a template for model
   contributions — pick `adding_a_model.md`, or open it directly:

   ```
   https://github.com/mdj2812/paperang-p2-lib/compare/main...YOUR-BRANCH?template=adding_a_model.md&expand=1
   ```

## Verification checklist

- [ ] USB connect and print
- [ ] Classic Bluetooth connect and print (skip only if the model has no SPP)
- [ ] `Paperang.auto_detect()` resolves the model
- [ ] Text, image, QR and pickup-code output fit the paper width
- [ ] `printer.print_pattern_test()` prints without clipping or skew
- [ ] Transport list in `transports` reflects what was actually tested
