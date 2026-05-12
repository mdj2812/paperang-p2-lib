"""Paperang P2 USB Printer — Backward-compat module.

Imports from :mod:`paperang.printer` and :mod:`paperang.printing`.
"""

from .printer import PaperangPrinter, PaperangP2, load_profiles, list_profiles

__all__ = ['PaperangPrinter', 'PaperangP2', 'load_profiles', 'list_profiles']
