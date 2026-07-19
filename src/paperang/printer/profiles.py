"""Paperang P2 — Print profile management."""

import json
import os


def load_profiles(profiles_path=None):
    """Load print profiles from JSON file."""
    if profiles_path and os.path.exists(profiles_path):
        try:
            with open(profiles_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    # Fallback to bundled profiles
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    bundled = os.path.join(pkg_dir, 'profiles.json')
    if os.path.exists(bundled):
        try:
            with open(bundled, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
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
