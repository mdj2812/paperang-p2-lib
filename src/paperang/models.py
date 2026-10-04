"""Hardware model descriptors for Paperang printers.

A :class:`PrinterModel` bundles the parameters that vary between Paperang
models — USB identifiers and print-head geometry.  Everything else (command
set, CRC, packet framing) is shared across the family.

Note the terminology split used throughout the package: a *model* is the
hardware, while a *profile* is a print-quality preset loaded via
:func:`paperang.printer.load_profiles`.

Adding a new model is a matter of adding a :class:`PrinterModel` entry to
:data:`MODELS` (or passing an instance to the printer directly, without
touching this module).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


class UnknownModelError(ValueError):
    """Raised when a model name cannot be resolved to a :class:`PrinterModel`."""


@dataclass(frozen=True)
class PrinterModel:
    """Parameters of a Paperang hardware model.

    Args:
        name: Human-readable model name, e.g. ``"P2"``.
        vid: USB vendor ID.
        pids: USB product IDs, primary first.
        print_width: Print-head width in dots.  Must be a positive multiple
            of 8, because the protocol sends one byte per 8 dots.
        heat_density: Default thermal density (0-100).
        feed_before: Default paper feed in lines before printing.
        feed_after: Default paper feed in lines after printing.
        aliases: Extra spellings this model is known by, e.g. names reported
            by ``CMD_GET_MODEL`` or used in the wild.  Matching ignores case
            and any non-alphanumeric characters, so ``"paperang_p2"``,
            ``"Paperang P2"`` and ``"PaperangP2"`` all collapse to one alias.
    """

    name: str
    vid: int
    pids: tuple[int, ...]
    print_width: int
    heat_density: int = 75
    feed_before: int = 50
    feed_after: int = 300
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


#: Built-in model: Paperang P2.
P2 = PrinterModel(
    name="P2",
    vid=0x4348,
    pids=(0x5584,),
    print_width=576,
    aliases=("paperang_p2",),
)

#: Registered hardware models, keyed by lower-case model name.
MODELS: dict[str, PrinterModel] = {
    "p2": P2,
}

#: Model used when none is specified.
DEFAULT_MODEL = "p2"

def _normalize_name(name: str) -> str:
    """Fold a model name for matching: lower-case, alphanumerics only."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _build_index() -> dict[str, PrinterModel]:
    """Map every accepted spelling to its model.

    The index is rebuilt per lookup so models added to :data:`MODELS` at
    runtime (and their aliases) are picked up without re-importing.
    """
    index: dict[str, PrinterModel] = {}
    for key, model in MODELS.items():
        index[_normalize_name(key)] = model
        index[_normalize_name(model.name)] = model
        for alias in model.aliases:
            index[_normalize_name(alias)] = model
    return index


def list_models() -> dict[str, PrinterModel]:
    """Return a copy of the registered models."""
    return dict(MODELS)


def get_model(model=None) -> PrinterModel:
    """Resolve *model* to a :class:`PrinterModel`.

    Args:
        model: ``None`` for the default model, a registered model name
            (case-insensitive), or an already-constructed
            :class:`PrinterModel` instance.

    Raises:
        UnknownModelError: The name is not registered.
        TypeError: The value is neither a name nor a PrinterModel.
    """
    if model is None:
        return MODELS[DEFAULT_MODEL]
    if isinstance(model, PrinterModel):
        return model
    if isinstance(model, str):
        resolved = _build_index().get(_normalize_name(model))
        if resolved is not None:
            return resolved
        known = ", ".join(sorted(MODELS))
        raise UnknownModelError(
            f"Unknown printer model {model!r}. Known models: {known}. "
            "Pass a PrinterModel instance to use a custom model."
        )
    raise TypeError(
        f"model must be None, a model name, or a PrinterModel, got {type(model).__name__}"
    )
