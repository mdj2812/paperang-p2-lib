"""Paperang — Print profile management."""

import json
import os


def _bundled_profiles_path():
    """Path of the profiles.json shipped inside the package.

    The file lives at the package root (``paperang/profiles.json``), one
    directory above this module, and is declared as package data in
    ``pyproject.toml``.
    """
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(pkg_root, 'profiles.json')


def load_profiles(profiles_path=None):
    """Load print profiles from a JSON file.

    Args:
        profiles_path: Explicit path to a profiles file.  When given it is the
            only file used: a missing or unreadable file yields ``{}``.  When
            None, the ``profiles.json`` bundled with the package is loaded.

    Returns:
        Mapping of profile name to settings, or ``{}`` if nothing could be
        loaded.
    """
    if profiles_path is None:
        profiles_path = _bundled_profiles_path()

    try:
        with open(profiles_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def list_profiles(profiles_path=None):
    """List available profiles."""
    profiles = load_profiles(profiles_path)
    print("Available profiles:")
    for name, settings in profiles.items():
        print(f"  {name}: {settings.get('description', 'No description')}")
        print(f"    threshold={settings.get('threshold', 128)}, "
              f"brightness={settings.get('brightness', 1.0)}, "
              f"contrast={settings.get('contrast', 1.0)}, "
              f"heat_density={settings.get('heat_density', 75)}")
