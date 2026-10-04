"""Tests for Paperang.auto_detect() and model resolution from a live device."""

import logging

import pytest

from paperang import (
    MODELS,
    Paperang,
    PrinterModel,
    UnknownModelError,
)
from paperang.constants import LINE_BYTES, PRINT_WIDTH
from paperang.models import models_for_usb, resolve_model, usb_pids
from paperang.printer import PaperangP2
from paperang.protocol import CMD_SENT_MODEL, pack_packet
from paperang.transport import Transport


class FakeTransport(Transport):
    """Transport that answers CMD_GET_MODEL with a canned model string."""

    def __init__(self, reported=None, vid=None, pid=None, matched_pid=None):
        self._reported = reported
        self.vid = vid
        self.pid = pid
        self.matched_pid = matched_pid
        self.connected = False
        self.sent = []

    def connect(self):
        self.connected = True
        return True

    def send(self, packet):
        self.sent.append(packet)

    def recv(self, timeout=1000):
        if not self._reported:
            return b""
        return pack_packet(CMD_SENT_MODEL, self._reported.encode())

    def disconnect(self):
        self.connected = False


class TestResolveModel:
    def test_by_usb_id(self):
        assert resolve_model(vid=0x4348, pid=0x5584).name == "P2"

    def test_by_reported_name(self):
        assert resolve_model(reported_name="Paperang_P2").name == "P2"

    def test_reported_name_wins_over_usb_id(self, caplog):
        # A stale table: this model uses another PID, but the device answered
        # on the P2 PID and reported a name that maps to it.
        other = PrinterModel(
            name="Other",
            vid=0x4348,
            pids=(0x5599,),
            print_width=384,
            aliases=("other_name",),
        )
        MODELS["other"] = other
        try:
            with caplog.at_level(logging.WARNING):
                resolved = resolve_model(
                    vid=0x4348, pid=0x5584, reported_name="other name"
                )
            assert resolved is other
            assert "trusting the reported model" in caplog.text
        finally:
            del MODELS["other"]

    def test_unknown_device(self):
        with pytest.raises(UnknownModelError, match="Could not identify"):
            resolve_model(vid=0x1111, pid=0x2222, reported_name="Nope")

    def test_unknown_device_message_is_actionable(self):
        with pytest.raises(UnknownModelError) as excinfo:
            resolve_model(vid=0x1111, pid=0x2222)
        message = str(excinfo.value)
        assert "1111:2222" in message
        assert "Known models" in message
        assert "model=" in message

    def test_usb_pids_covers_registered_models(self):
        assert 0x5584 in usb_pids()

    def test_models_for_usb(self):
        assert models_for_usb(0x4348, 0x5584) == (MODELS["p2"],)
        assert models_for_usb(0x4348, 0x9999) == ()


class TestAutoDetect:
    def test_resolves_from_usb_id(self):
        transport = FakeTransport(vid=0x4348, matched_pid=0x5584)
        printer = Paperang.auto_detect(transport=transport)

        assert transport.connected
        assert printer.printer_model.name == "P2"
        assert printer.print_width == PRINT_WIDTH
        assert printer.line_bytes == LINE_BYTES

    def test_resolves_from_reported_name_without_usb_ids(self):
        """Bluetooth has no VID/PID, so the reported name is the only signal."""
        transport = FakeTransport(reported="Paperang_P2")
        printer = Paperang.auto_detect(transport=transport)

        assert printer.printer_model.name == "P2"

    def test_usb_id_wins_when_the_printer_stays_silent(self):
        transport = FakeTransport(vid=0x4348, matched_pid=0x5584)
        printer = Paperang.auto_detect(transport=transport)
        assert printer.printer_model.name == "P2"

    def test_reported_name_overrides_usb_id(self, caplog):
        # Same shape as above, driven through auto_detect().
        other = PrinterModel(
            name="D1",
            vid=0x4348,
            pids=(0x5585,),
            print_width=384,
            aliases=("paperang_d1",),
        )
        MODELS["d1"] = other
        try:
            transport = FakeTransport(
                reported="Paperang_D1", vid=0x4348, matched_pid=0x5584
            )
            with caplog.at_level(logging.WARNING):
                printer = Paperang.auto_detect(transport=transport)
            assert printer.printer_model is other
            assert printer.print_width == 384
        finally:
            del MODELS["d1"]

    def test_unknown_device_raises(self):
        transport = FakeTransport(vid=0x1111, matched_pid=0x2222)
        with pytest.raises(UnknownModelError):
            Paperang.auto_detect(transport=transport)

    def test_kwargs_are_passed_through(self):
        transport = FakeTransport(vid=0x4348, matched_pid=0x5584)
        printer = Paperang.auto_detect(
            transport=transport, font_paths_text=["/tmp/font.ttf"]
        )
        assert printer.font_paths_text == ["/tmp/font.ttf"]

    def test_available_on_both_class_names(self):
        for cls in (Paperang, PaperangP2):
            transport = FakeTransport(vid=0x4348, matched_pid=0x5584)
            printer = cls.auto_detect(transport=transport)
            assert isinstance(printer, cls)

    def test_default_transport_searches_every_registered_pid(self, monkeypatch):
        captured = {}

        class CaptureTransport(FakeTransport):
            def __init__(self, **kwargs):
                super().__init__(vid=kwargs.get("vid"), matched_pid=0x5584)
                captured.update(kwargs)

        monkeypatch.setattr(
            "paperang.printer._printing.UsbTransport", CaptureTransport
        )
        Paperang.auto_detect()

        assert captured["pids"] == usb_pids()
        assert captured["vid"] == MODELS["p2"].vid
