"""Geometry tests parameterized over every registered model.

These run against the model registry rather than a hand-written model, so
adding a model JSON file extends coverage automatically.
"""

import struct

import pytest

from paperang import PrinterModel, list_models
from paperang.printer import Paperang
from paperang.protocol import MAX_PACKET_DATA
from paperang.transport import Transport

# Every registered model, plus a synthetic 384-dot head standing in for the D1
# until #22 adds it, so the 384/48 geometry is exercised today.
TEST_384 = PrinterModel(
    name="TEST-384", vid=0x4348, pids=(0x5599,), print_width=384,
)

MODEL_CASES = sorted(list_models().items()) + [("test-384", TEST_384)]


class MockTransport(Transport):
    """Captures everything sent, answers nothing."""

    def __init__(self):
        self.sent_packets = []

    def connect(self):
        return True

    def send(self, packet):
        self.sent_packets.append(packet)

    def recv(self, timeout=1000):
        return b""

    def disconnect(self):
        pass


def bitmap_payloads(transport):
    """Bitmap data of every CMD_PRINT_BITMAP packet, as separate chunks."""
    payloads = []
    for packet in transport.sent_packets:
        if len(packet) < 10 or packet[1] != 0x00:
            continue
        data_len = struct.unpack_from("<H", packet, 3)[0]
        payloads.append(packet[5:5 + data_len])
    return payloads


@pytest.fixture(params=MODEL_CASES, ids=lambda case: case[0])
def model(request):
    """Every registered model."""
    return request.param[1]


@pytest.fixture
def printer(model):
    transport = MockTransport()
    return Paperang(transport, model=model), transport


def test_the_matrix_covers_every_registered_model():
    """Guard: the matrix follows the model files, not a hardcoded list."""
    assert set(list_models()) <= {key for key, _ in MODEL_CASES}


def test_the_matrix_covers_both_head_widths():
    widths = {model.print_width for _, model in MODEL_CASES}
    assert 576 in widths
    assert 384 in widths


def test_geometry_is_self_consistent(model):
    assert model.print_width > 0
    assert model.print_width % 8 == 0
    assert model.line_bytes == model.print_width // 8


class TestBitmapAlignment:
    def test_default_width_matches_the_head(self, model, printer):
        instance, transport = printer
        assert instance.line_bytes == model.line_bytes

        rows = (MAX_PACKET_DATA // model.line_bytes) + 3
        instance.print_bitmap(b"\x00" * model.line_bytes * rows)

        payloads = bitmap_payloads(transport)
        assert payloads
        assert all(len(p) % model.line_bytes == 0 for p in payloads)
        assert sum(len(p) for p in payloads) == model.line_bytes * rows

    def test_packets_hold_at_most_one_payload_each(self, model, printer):
        instance, transport = printer
        rows = (MAX_PACKET_DATA // model.line_bytes) + 1
        instance.print_bitmap(b"\xff" * model.line_bytes * rows)

        per_packet = MAX_PACKET_DATA // model.line_bytes
        for payload in bitmap_payloads(transport):
            assert len(payload) <= per_packet * model.line_bytes

    def test_pattern_test_produces_full_rows(self, model, printer):
        instance, transport = printer
        instance.print_pattern_test()

        payloads = bitmap_payloads(transport)
        assert payloads
        assert all(len(p) % model.line_bytes == 0 for p in payloads)

    def test_heat_density_test_produces_full_rows(self, model, printer):
        instance, transport = printer
        instance.print_heat_density_test()

        payloads = bitmap_payloads(transport)
        assert payloads
        assert all(len(p) % model.line_bytes == 0 for p in payloads)


class TestRenderedOutput:
    def _write_image(self, path, size=(100, 50)):
        from PIL import Image

        image = Image.new("L", size)
        image.putdata([(i * 7) % 256 for i in range(size[0] * size[1])])
        image.save(path)
        return path

    def test_image_is_scaled_to_the_head_width(self, model, printer, tmp_path):
        instance, transport = printer
        source = self._write_image(str(tmp_path / "in.png"))

        instance.print_image(source)

        expected_rows = int(50 * model.print_width / 100)
        total = sum(len(p) for p in bitmap_payloads(transport))
        assert total == model.line_bytes * expected_rows

    def test_vertical_image_rows_stay_aligned(self, model, printer, tmp_path):
        instance, transport = printer
        source = self._write_image(str(tmp_path / "in.png"))

        instance.print_image(source, vertical=True)

        payloads = bitmap_payloads(transport)
        assert payloads
        assert all(len(p) % model.line_bytes == 0 for p in payloads)

    def test_text_rows_stay_aligned(self, model, printer):
        instance, transport = printer
        instance.print_text("Hello 123")

        payloads = bitmap_payloads(transport)
        assert payloads
        assert all(len(p) % model.line_bytes == 0 for p in payloads)

    def test_qr_rows_stay_aligned(self, model, printer):
        pytest.importorskip("qrcode")
        instance, transport = printer

        instance.print_qr("https://example.com/x")

        payloads = bitmap_payloads(transport)
        assert payloads
        assert all(len(p) % model.line_bytes == 0 for p in payloads)


class TestPaperangP2StillUnchanged:
    """Explicit assertions for the default model, independent of the matrix."""

    def test_default_geometry(self):
        printer = Paperang(MockTransport())
        assert printer.print_width == 576
        assert printer.line_bytes == 72

    def test_default_bitmap_row_width(self):
        transport = MockTransport()
        Paperang(transport).print_bitmap(b"\x00" * 72 * 5)
        assert bitmap_payloads(transport) == [b"\x00" * 72 * 5]
