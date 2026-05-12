"""Paperang P2 — Printer / application layer.

High-level printer interface, printing functions, and profile management.
"""

from ._base import PaperangPrinter
from ._printing import PaperangP2
from .profiles import load_profiles, list_profiles

__all__ = [
    "PaperangPrinter",
    "PaperangP2",
    "load_profiles",
    "list_profiles",
]
