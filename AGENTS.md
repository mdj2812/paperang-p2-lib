# Repository notes for coding agents

## Pull requests

- **Adding or changing a printer model:** start the PR body from
  [`.github/PULL_REQUEST_TEMPLATE/adding_a_model.md`](.github/PULL_REQUEST_TEMPLATE/adding_a_model.md)
  and fill it in. `gh pr create` does not pick up named templates in
  `.github/PULL_REQUEST_TEMPLATE/`, so read the file and pass it with
  `--body-file`.
- Fill the fields honestly: a value that has not been measured is written as
  such ("not observed yet", "community report") rather than inferred silently.
  The template's checkboxes exist to make gaps visible, not to be ticked.
- Other changes: keep the body short, but always state what was verified and
  what was not.

## Checks before opening a PR

```bash
python -m pytest
ruff check src/
```

CI pins the ruff rule set in `pyproject.toml`; the lint job uses `ruff check src/`
against the current tree.

## Conventions

- **Model vs profile.** A *model* is the hardware — a JSON file under
  `src/paperang/models/`. A *profile* is a print-quality preset in
  `profiles.json`. They are separate on purpose: print settings (heat density,
  paper feed) in a model file are rejected as unknown fields.
- **Add data, not code.** New models, aliases and transport details belong in a
  model JSON file; the loader validates the fields.
- **Downstream syntax is a contract.** `paperang-hacs`, `paperang-p2-usb` and
  `wyrtensi/paperang-cli` depend on the import paths, the `UsbTransport`
  constructor signature and its `_dev` / `_ep_out` / `_ep_in` attributes. Check
  them before renaming anything.
- **P2 output is byte-for-byte stable.** Changes to the rendering path are
  compared against a known-good build; see the print-path A/B checks in the
  pull requests referenced by the CHANGELOG.

## Documentation map

- `README.md` — install, usage, API reference.
- `MODELS.md` — supported models, identification, verification status.
- `docs/adding-a-model.md` — field reference and hardware checklist.
