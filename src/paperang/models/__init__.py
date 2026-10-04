"""Hardware model descriptors for Paperang printers.

Each supported printer ships as a small JSON file in this package
(``p2.json``, ``d1.json``, ...).  Those files are the source of truth for
model data; :class:`PrinterModel` is the runtime type and the single place
where the data is validated, so JSON never has to restate rules such as
``line_bytes`` or the ``print_width % 8 == 0`` requirement.

Note the terminology split used throughout the package: a *model* is the
hardware, while a *profile* is a print-quality preset loaded via
:func:`paperang.printer.load_profiles`.

Adding a model means adding a JSON file, or passing a path to one (or a
``PrinterModel`` instance) to the printer directly — no library changes needed.
"""

from __future__ import annotations

import glob
import json
import os
import re
from dataclasses import dataclass, fields


class UnknownModelError(ValueError):
    """Raised when a model name cannot be resolved to a :class:`PrinterModel`."""


class InvalidModelError(ValueError):
    """Raised when a model file is malformed or fails validation."""


def _as_int(value, field_name: str) -> int:
    """Coerce a JSON value to int, accepting strings such as ``"0x5584"``."""
    if isinstance(value, bool):
        raise InvalidModelError(f"{field_name} must be an integer, got {value!r}")
    try:
        return int(value, 0) if isinstance(value, str) else int(value)
    except (TypeError, ValueError):
        raise InvalidModelError(
            f"{field_name} must be an integer, got {value!r}"
        ) from None


@dataclass(frozen=True)
class PrinterModel:
    """Parameters of a Paperang hardware model.

    A model describes what the hardware *is*: identity (name, USB ids, aliases)
    and geometry (print-head width).  Print settings such as heat density and
    paper feed are job-level values — they belong to the print profiles
    (:func:`paperang.printer.load_profiles`) or to the individual call, and
    deliberately do not live here.

    Args:
        name: Human-readable model name, e.g. ``"P2"``.
        vid: USB vendor ID.
        pids: USB product IDs, primary first.
        print_width: Print-head width in dots.  Must be a positive multiple
            of 8, because the protocol sends one byte per 8 dots.
        aliases: Extra spellings this model is known by, e.g. names reported
            by ``CMD_GET_MODEL`` or used in the wild.  Matching ignores case
            and any non-alphanumeric characters, so ``"paperang_p2"``,
            ``"Paperang P2"`` and ``"PaperangP2"`` all collapse to one alias.
    """

    name: str
    vid: int
    pids: tuple[int, ...]
    print_width: int
    aliases: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.pids:
            raise ValueError(f"{self.name}: at least one USB product ID is required")
        if self.print_width <= 0 or self.print_width % 8 != 0:
            raise ValueError(
                f"{self.name}: print_width must be a positive multiple of 8, "
                f"got {self.print_width}"
            )

    @property
    def pid(self) -> int:
        """Primary USB product ID."""
        return self.pids[0]

    @property
    def line_bytes(self) -> int:
        """Bytes per bitmap row: ``print_width // 8``."""
        return self.print_width // 8

    @classmethod
    def from_dict(cls, data, source=None) -> "PrinterModel":
        """Build a model from a JSON mapping.

        Args:
            data: Parsed JSON object.
            source: File path or description used in error messages.

        Raises:
            InvalidModelError: A field is unknown, missing, or invalid.
        """
        where = f" in {source}" if source else ""
        if not isinstance(data, dict):
            raise InvalidModelError(f"model definition{where} must be a JSON object")

        known = {field.name for field in fields(cls)}
        unknown = sorted(set(data) - known)
        if unknown:
            raise InvalidModelError(
                f"unknown field(s){where}: {', '.join(unknown)}. "
                f"Known fields: {', '.join(sorted(known))}"
            )

        missing = [n for n in ("name", "vid", "pids", "print_width") if n not in data]
        if missing:
            raise InvalidModelError(
                f"missing required field(s){where}: {', '.join(missing)}"
            )

        pids = data["pids"]
        if not isinstance(pids, (list, tuple)):
            raise InvalidModelError(f"pids{where} must be a list of integers")

        aliases = data.get("aliases", ())
        if not isinstance(aliases, (list, tuple)):
            raise InvalidModelError(f"aliases{where} must be a list of strings")

        try:
            return cls(
                name=str(data["name"]),
                vid=_as_int(data["vid"], "vid"),
                pids=tuple(_as_int(p, "pids") for p in pids),
                print_width=_as_int(data["print_width"], "print_width"),
                aliases=tuple(str(a) for a in aliases),
            )
        except InvalidModelError:
            raise
        except ValueError as exc:
            raise InvalidModelError(f"invalid model definition{where}: {exc}") from None


def _models_dir() -> str:
    """Directory holding the bundled model JSON files."""
    return os.path.dirname(os.path.abspath(__file__))


def load_model_file(path) -> PrinterModel:
    """Load a single model definition from a JSON file.

    Raises:
        InvalidModelError: The file is unreadable, not JSON, or invalid.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except OSError as exc:
        raise InvalidModelError(f"cannot read model file {path}: {exc}") from None
    except json.JSONDecodeError as exc:
        raise InvalidModelError(f"{path} is not valid JSON: {exc}") from None
    return PrinterModel.from_dict(data, source=str(path))


def _load_bundled_models() -> dict:
    models = {}
    for path in sorted(glob.glob(os.path.join(_models_dir(), "*.json"))):
        key = os.path.splitext(os.path.basename(path))[0].lower()
        models[key] = load_model_file(path)
    return models


#: Registered hardware models, keyed by the model file name (lower-case).
#: Populated from the bundled JSON files; extra entries can be added at
#: runtime, and are honoured by :func:`get_model`.
MODELS: dict = _load_bundled_models()

#: Model used when none is specified.
DEFAULT_MODEL = "p2"

if DEFAULT_MODEL not in MODELS:
    raise InvalidModelError(f"bundled model file {DEFAULT_MODEL}.json is missing")

#: The built-in default model instance.
P2 = MODELS[DEFAULT_MODEL]


def _normalize_name(name: str) -> str:
    """Fold a model name for matching: lower-case, alphanumerics only."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _build_index() -> dict:
    """Map every accepted spelling to its model.

    The index is rebuilt per lookup so models added to :data:`MODELS` at
    runtime (and their aliases) are picked up without re-importing.
    """
    index = {}
    for key, model in MODELS.items():
        index[_normalize_name(key)] = model
        index[_normalize_name(model.name)] = model
        for alias in model.aliases:
            index[_normalize_name(alias)] = model
    return index


def list_models() -> dict:
    """Return a copy of the registered models."""
    return dict(MODELS)


def get_model(model=None) -> PrinterModel:
    """Resolve *model* to a :class:`PrinterModel`.

    Args:
        model: ``None`` for the default model, a registered model name or
            alias (case-insensitive), a path to a model JSON file, or an
            already-constructed :class:`PrinterModel` instance.

    Raises:
        UnknownModelError: The name is not registered and is not a file path.
        InvalidModelError: A model file is malformed or invalid.
        TypeError: The value is not a name, path, or PrinterModel.
    """
    if model is None:
        return MODELS[DEFAULT_MODEL]
    if isinstance(model, PrinterModel):
        return model
    if isinstance(model, str):
        text = model.strip()
        resolved = _build_index().get(_normalize_name(text))
        if resolved is not None:
            return resolved
        if text.lower().endswith(".json") or os.path.exists(text):
            return load_model_file(text)
        known = ", ".join(sorted(MODELS))
        raise UnknownModelError(
            f"Unknown printer model {model!r}. Known models: {known}. "
            "Pass a path to a model JSON file or a PrinterModel instance to use "
            "a custom model."
        )
    raise TypeError(
        f"model must be None, a model name, a path, or a PrinterModel, "
        f"got {type(model).__name__}"
    )
