"""Paperang P2 USB Printer — Backward-compat module.

Imports from :mod:`paperang.printer` and :mod:`paperang.printing`.
"""

from .printer import Paperang, PaperangP2, PaperangPrinter, load_profiles, list_profiles

__all__ = [
    'PaperangPrinter', 'Paperang', 'PaperangP2', 'load_profiles', 'list_profiles',
]
