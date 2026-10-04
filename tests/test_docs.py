"""Consistency checks between the model table and the documentation."""

import os

from paperang import MODELS

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(REPO_ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_every_model_is_documented():
    """A new model file must be added to the README table too."""
    readme = _read("README.md")
    for key, model in MODELS.items():
        assert model.name in readme, f"model {key!r} is missing from README.md"
        for pid in model.pids:
            assert f"0x{pid:04x}" in readme, (
                f"PID 0x{pid:04x} of model {key!r} is missing from README.md"
            )


def test_adding_a_model_guide_exists():
    guide = _read("docs", "adding-a-model.md")
    assert "print_width" in guide
    assert "CMD_GET_MODEL" in guide


def test_guide_documents_the_alias_requirement():
    """The CMD_GET_MODEL spelling must be listed as an alias."""
    guide = _read("docs", "adding-a-model.md")
    assert "aliases" in guide
