"""Tests for paperang.printer.profiles — profile management."""

import json
import os
import tempfile

from paperang.printer.profiles import load_profiles, list_profiles


def test_load_profiles_with_test_data():
    """Load profiles from a temporary file."""
    profiles_data = {
        "portrait": {
            "threshold": 180,
            "brightness": 1.5,
            "contrast": 0.6,
            "heat_density": 80,
        },
        "landscape": {"threshold": 160, "heat_density": 70},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(profiles_data, f)
        path = f.name

    try:
        profiles = load_profiles(path)
        assert profiles == profiles_data
    finally:
        os.unlink(path)


def test_load_profiles_missing_file():
    """Missing file should return empty dict."""
    profiles = load_profiles("/nonexistent/path/profiles.json")
    assert profiles == {}


def test_load_profiles_invalid_json():
    """Invalid JSON should return empty dict."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json{{{")
        path = f.name

    try:
        profiles = load_profiles(path)
        assert profiles == {}
    finally:
        os.unlink(path)


def test_list_profiles_empty(capsys):
    """list_profiles with no profiles should print empty line."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({}, f)
        path = f.name

    try:
        list_profiles(path)
        captured = capsys.readouterr()
        # Should not crash, even with empty profiles
    finally:
        os.unlink(path)


def test_list_profiles_with_data(capsys):
    """list_profiles should print profile names."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"test_profile": {"threshold": 128}}, f)
        path = f.name

    try:
        list_profiles(path)
        captured = capsys.readouterr()
        assert "test_profile" in captured.out
    finally:
        os.unlink(path)


def test_load_profiles_default_path():
    """load_profiles with default path should not crash."""
    import paperang.printer.profiles as mod
    default = os.path.join(os.path.dirname(mod.__file__), "profiles.json")
    profiles = load_profiles()
    assert isinstance(profiles, dict)
