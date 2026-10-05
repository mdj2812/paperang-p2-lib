"""Paperang P2 — Transport ABC (abstract base class)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Transport(ABC):
    """Abstract transport for Paperang P2 communication.

    Each transport provides raw byte-level send/recv.
    The protocol layer (packet framing, CRC, command codes)
    lives in :mod:`paperang.printer` and does not depend on
    the transport type.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the printer.

        Returns:
            True on success.
        Raises:
            RuntimeError if the printer is not found.
        """

    @abstractmethod
    def send(self, packet: bytes) -> None:
        """Send raw packet bytes to the printer."""

    @abstractmethod
    def recv(self, timeout: int = 1000) -> bytes:
        """Receive raw bytes from the printer.

        Args:
            timeout: Read timeout in milliseconds.

        Returns:
            Raw bytes received, or empty ``b''`` on timeout / error.
        """

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection and release resources."""
