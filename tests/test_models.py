"""Tests for paperang.models and model-driven print geometry.

Covers the P2 defaults staying intact and a non-P2 model (a 384-dot head,
the geometry reported for the Paperang D1) driving everything correctly.
"""

import json
import os

import pytest

from paperang import (
    DEFAULT_MODEL,
    MODELS,
    InvalidModelError,
    PrinterModel,
    UnknownModelError,
    get_model,
    list_models,
    load_model_file,
)
from paperang.constants import (
    LINE_BYTES,
    PRINT_WIDTH,
    PRODUCT_ID,
    VENDOR_ID,
)
from paperang.models import P2
from paperang.printer import PaperangP2, PaperangPrinter
from paperang.protocol import CMD_PRINT_BITMAP, MAX_PACKET_DATA, unpack_response
from paperang.transport import Transport, UsbTransport

# A 384-dot model, matching the parameters reported for the Paperang D1.
MODEL_384 = PrinterModel(
    name="TEST-384",
    vid=0x4348,
    pids=(0x5585,),
    print_width=384,
)


class MockTransport(Transport):
    """Controllable transport for unit tests."""

    def __init__(self, response_data=None):
        self.sent_packets = []
        self._response = response_data or b""
        self.connected = False

    def connect(self):
        self.connected = True
        return True

    def send(self, packet):
        self.sent_packets.append(packet)

    def recv(self, timeout=1000):
        return self._response

    def disconnect(self):
        self.connected = False


def bitmap_payloads(transport):
    """Return the bitmap data of every CMD_PRINT_BITMAP packet sent."""
    payloads = []
    for packet in transport.sent_packets:
        for frame in unpack_response(packet):
            if frame["cmd"] == CMD_PRINT_BITMAP:
                payloads.append(frame["data"])
    return payloads


class TestModelRegistry:
    def test_default_model(self):
        assert get_model() is P2
        assert get_model(None) is P2
        assert get_model(DEFAULT_MODEL) is P2

    def test_lookup_is_case_insensitive(self):
        assert get_model("p2") is P2
        assert get_model("P2") is P2
        assert get_model("  p2  ") is P2

    def test_aliases(self):
        assert get_model("paperang_p2") is P2
        assert get_model("PaperangP2") is P2
        assert get_model("Paperang P2") is P2
        assert get_model("paperang-p2") is P2
        assert get_model("PAPERANG_P2") is P2

    def test_alias_comes_from_the_model(self):
        model = PrinterModel(
            name="Test 384",
            vid=0x4348,
            pids=(0x5585,),
            print_width=384,
            aliases=("paperang_d1", "ZYB-D1"),
        )
        MODELS["test384"] = model
        try:
            assert get_model("Test384") is model
            assert get_model("test 384") is model
            assert get_model("paperang_d1") is model
            assert get_model("zyb-d1") is model
        finally:
            del MODELS["test384"]

    def test_runtime_registered_model_is_found(self):
        model = PrinterModel(name="Hot Plug", vid=1, pids=(9,), print_width=384)
        MODELS["hotplug"] = model
        try:
            assert get_model("hotplug") is model
            assert get_model("Hot Plug") is model
        finally:
            del MODELS["hotplug"]
        with pytest.raises(UnknownModelError):
            get_model("hotplug")

    def test_instance_passthrough(self):
        assert get_model(MODEL_384) is MODEL_384

    def test_unknown_name(self):
        with pytest.raises(UnknownModelError) as excinfo:
            get_model("nope")
        message = str(excinfo.value)
        assert "nope" in message
        assert "p2" in message

    def test_bad_type(self):
        with pytest.raises(TypeError):
            get_model(123)

    def test_list_models_returns_copy(self):
        models = list_models()
        assert models == MODELS
        models["fake"] = MODEL_384
        assert "fake" not in MODELS

    def test_known_models_are_printer_models(self):
        for name, model in MODELS.items():
            assert isinstance(model, PrinterModel)
            assert model.name


class TestPrinterModel:
    def test_line_bytes_derived(self):
        assert P2.line_bytes == 72
        assert MODEL_384.line_bytes == 48

    def test_primary_pid(self):
        assert P2.pid == 0x5584
        assert MODEL_384.pid == 0x5585

    def test_multi_pid_model(self):
        model = PrinterModel(name="X", vid=1, pids=(2, 3), print_width=384)
        assert model.pid == 2

    @pytest.mark.parametrize("width", [0, -8, 100, 1002])
    def test_invalid_print_width(self, width):
        with pytest.raises(ValueError, match="multiple of 8"):
            PrinterModel(name="X", vid=1, pids=(2,), print_width=width)

    def test_missing_pids(self):
        with pytest.raises(ValueError, match="product ID"):
            PrinterModel(name="X", vid=1, pids=(), print_width=384)


class TestConstantsStayP2:
    def test_constants_track_the_p2_model(self):
        assert (VENDOR_ID, PRODUCT_ID) == (P2.vid, P2.pid)
        assert (PRINT_WIDTH, LINE_BYTES) == (P2.print_width, P2.line_bytes)

    def test_usb_transport_defaults(self):
        transport = UsbTransport()
        assert transport.vid == P2.vid
        assert transport.pid == P2.pid


def write_model(tmp_path, payload, name="custom.json"):
    """Write a model JSON file and return its path."""
    path = tmp_path / name
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


class TestModelFiles:
    """Model data comes from per-model JSON files."""

    def test_bundled_file_is_the_source_of_truth(self):
        import paperang.models

        model_dir = os.path.dirname(os.path.abspath(paperang.models.__file__))
        assert os.path.exists(os.path.join(model_dir, "p2.json"))

        loaded = load_model_file(os.path.join(model_dir, "p2.json"))
        assert loaded == MODELS["p2"]
        assert (loaded.vid, loaded.pid) == (0x4348, 0x5584)
        assert loaded.print_width == 576
        assert loaded.line_bytes == 72

    def test_all_bundled_files_are_registered(self):
        import paperang.models

        model_dir = os.path.dirname(os.path.abspath(paperang.models.__file__))
        files = {f[:-5] for f in os.listdir(model_dir) if f.endswith(".json")}
        assert files == set(MODELS)

    def test_hex_and_decimal_ids_are_equivalent(self, tmp_path):
        hex_path = write_model(tmp_path, {
            "name": "H",
            "vid": "0x4348",
            "pids": ["0x5585"],
            "print_width": 384,
        }, "hex.json")
        dec_path = write_model(tmp_path, {
            "name": "D",
            "vid": 17224,
            "pids": [21893],
            "print_width": 384,
        }, "dec.json")

        assert get_model(hex_path).vid == get_model(dec_path).vid == 0x4348
        assert get_model(hex_path).pids == get_model(dec_path).pids == (0x5585,)

    def test_minimal_file_only_needs_identity_and_geometry(self, tmp_path):
        path = write_model(tmp_path, {
            "name": "Minimal",
            "vid": 1,
            "pids": [2],
            "print_width": 384,
        })
        model = get_model(path)
        assert model.name == "Minimal"
        assert model.line_bytes == 48
        assert model.aliases == ()

    @pytest.mark.parametrize(
        "field", ["heat_density", "feed_before", "feed_after"]
    )
    def test_print_settings_are_not_model_data(self, tmp_path, field):
        """Density and feed are job-level settings, not model properties."""
        path = write_model(tmp_path, {
            "name": "X",
            "vid": 1,
            "pids": [2],
            "print_width": 384,
            field: 75,
        })
        with pytest.raises(InvalidModelError, match="unknown field"):
            load_model_file(path)

    def test_aliases_from_file(self, tmp_path):
        path = write_model(tmp_path, {
            "name": "Test 384",
            "vid": 1,
            "pids": [2],
            "print_width": 384,
            "aliases": ["paperang_d1", "ZYB-D1"],
        })
        model = get_model(path)
        assert model.aliases == ("paperang_d1", "ZYB-D1")

    def test_model_path_in_get_model(self, tmp_path):
        path = write_model(tmp_path, {
            "name": "From File",
            "vid": 1,
            "pids": [2],
            "print_width": 384,
        })
        assert get_model(path).print_width == 384

    def test_printer_accepts_model_path(self, tmp_path):
        path = write_model(tmp_path, {
            "name": "From File",
            "vid": 0x4348,
            "pids": [0x5585],
            "print_width": 384,
        })
        printer = PaperangPrinter(MockTransport(), model=path)
        assert printer.print_width == 384
        assert printer.line_bytes == 48

    def test_unknown_field_rejected(self, tmp_path):
        path = write_model(tmp_path, {
            "name": "X",
            "vid": 1,
            "pids": [2],
            "print_width": 384,
            "line_bytes": 48,
        })
        with pytest.raises(InvalidModelError, match="unknown field"):
            load_model_file(path)

    def test_missing_required_field_rejected(self, tmp_path):
        path = write_model(tmp_path, {
            "name": "X",
            "vid": 1,
            "print_width": 384,
        })
        with pytest.raises(InvalidModelError, match="missing required field"):
            load_model_file(path)

    def test_invalid_print_width_rejected(self, tmp_path):
        path = write_model(tmp_path, {
            "name": "X",
            "vid": 1,
            "pids": [2],
            "print_width": 100,
        })
        with pytest.raises(InvalidModelError, match="multiple of 8"):
            load_model_file(path)

    def test_bad_pids_type_rejected(self, tmp_path):
        path = write_model(tmp_path, {
            "name": "X",
            "vid": 1,
            "pids": 5585,
            "print_width": 384,
        })
        with pytest.raises(InvalidModelError, match="pids"):
            load_model_file(path)

    def test_malformed_json_rejected(self, tmp_path):
        path = write_model(tmp_path, "{not json", "broken.json")
        with pytest.raises(InvalidModelError, match="not valid JSON"):
            load_model_file(path)

    def test_bluetooth_metadata_is_loaded(self, tmp_path):
        path = write_model(tmp_path, {
            "name": "BT Model",
            "vid": 0x4348,
            "pids": [0x5599],
            "print_width": 384,
            "transports": ["usb", "spp"],
            "bt_name_prefixes": ["Paperang_X"],
            "bt_service_uuids": ["0000fee7-0000-1000-8000-00805F9B34FB"],
            "bt_rfcomm_channel": 3,
        })
        model = get_model(path)
        assert model.supports_usb and model.supports_bluetooth
        assert model.bt_name_prefixes == ("paperang_x",)
        assert model.bt_service_uuids == ("0000fee7-0000-1000-8000-00805f9b34fb",)
        assert model.bt_rfcomm_channel == 3

    def test_defaults_when_metadata_is_absent(self, tmp_path):
        path = write_model(tmp_path, {
            "name": "Minimal",
            "vid": 1,
            "pids": [2],
            "print_width": 384,
        })
        model = get_model(path)
        assert model.transports == ("usb", "spp")
        assert model.bt_name_prefixes == ()
        assert model.bt_service_uuids == ()
        assert model.bt_rfcomm_channel is None

    def test_unsupported_transport_rejected(self, tmp_path):
        path = write_model(tmp_path, {
            "name": "X",
            "vid": 1,
            "pids": [2],
            "print_width": 384,
            "transports": ["usb", "ble"],
        })
        with pytest.raises(InvalidModelError, match="unsupported transport"):
            load_model_file(path)

    def test_bad_service_uuid_rejected(self, tmp_path):
        path = write_model(tmp_path, {
            "name": "X",
            "vid": 1,
            "pids": [2],
            "print_width": 384,
            "bt_service_uuids": ["fee7"],
        })
        with pytest.raises(InvalidModelError, match="128-bit UUID"):
            load_model_file(path)

    @pytest.mark.parametrize("channel", [0, 31, -1])
    def test_bad_rfcomm_channel_rejected(self, tmp_path, channel):
        path = write_model(tmp_path, {
            "name": "X",
            "vid": 1,
            "pids": [2],
            "print_width": 384,
            "bt_rfcomm_channel": channel,
        })
        with pytest.raises(InvalidModelError, match="between 1 and 30"):
            load_model_file(path)

    def test_missing_file_rejected(self, tmp_path):
        with pytest.raises(InvalidModelError, match="cannot read"):
            load_model_file(str(tmp_path / "nope.json"))

    def test_error_message_names_the_file(self, tmp_path):
        path = write_model(tmp_path, {
            "name": "X",
            "vid": 1,
            "pids": [2],
            "print_width": 100,
        })
        with pytest.raises(InvalidModelError) as excinfo:
            load_model_file(path)
        assert "custom.json" in str(excinfo.value)


class TestPrinterGeometry:
    def test_defaults_to_p2(self):
        printer = PaperangPrinter(MockTransport())
        assert printer.printer_model is P2
        assert printer.print_width == 576
        assert printer.line_bytes == 72

    def test_accepts_model_name(self):
        printer = PaperangPrinter(MockTransport(), model="p2")
        assert printer.printer_model is P2

    def test_accepts_model_instance(self):
        printer = PaperangPrinter(MockTransport(), model=MODEL_384)
        assert printer.print_width == 384
        assert printer.line_bytes == 48

    def test_default_transport_follows_model(self):
        printer = PaperangPrinter(model=MODEL_384)
        assert isinstance(printer._transport, UsbTransport)
        assert printer._transport.vid == MODEL_384.vid
        assert printer._transport.pid == MODEL_384.pid

    def test_high_level_accepts_model(self):
        printer = PaperangP2(MockTransport(), model=MODEL_384)
        assert printer.print_width == 384
        assert printer.line_bytes == 48


class TestPrintBitmapGeometry:
    def test_default_width_uses_model(self):
        transport = MockTransport()
        printer = PaperangPrinter(transport, model=MODEL_384)
        printer.print_bitmap(b"\xFF" * 48 * 3)
        payloads = bitmap_payloads(transport)
        assert len(payloads) == 1
        assert len(payloads[0]) == 48 * 3

    def test_default_width_is_p2_line_bytes(self):
        transport = MockTransport()
        printer = PaperangPrinter(transport)
        printer.print_bitmap(b"\xFF" * 72 * 5)
        assert len(bitmap_payloads(transport)[0]) == 72 * 5

    def test_explicit_width_still_honoured(self):
        transport = MockTransport()
        printer = PaperangPrinter(transport, model=MODEL_384)
        printer.print_bitmap(b"\xFF" * 72 * 2, width_bytes=72)
        assert len(bitmap_payloads(transport)[0]) == 72 * 2

    def test_lines_per_packet_follows_line_bytes(self):
        for model in (P2, MODEL_384):
            transport = MockTransport()
            printer = PaperangPrinter(transport, model=model)
            lines = MAX_PACKET_DATA // model.line_bytes + 5
            printer.print_bitmap(b"\x00" * model.line_bytes * lines)

            payloads = bitmap_payloads(transport)
            expected_per_packet = MAX_PACKET_DATA // model.line_bytes
            assert all(
                len(payload) % model.line_bytes == 0 for payload in payloads
            )
            assert all(
                len(payload) <= expected_per_packet * model.line_bytes
                for payload in payloads
            )
            assert sum(len(p) for p in payloads) == model.line_bytes * lines

    @pytest.mark.parametrize("width_bytes", [0, -1, MAX_PACKET_DATA + 1])
    def test_invalid_width_bytes(self, width_bytes):
        printer = PaperangPrinter(MockTransport())
        with pytest.raises(ValueError):
            printer.print_bitmap(b"\xFF" * 100, width_bytes=width_bytes)


class TestHighLevelGeometry:
    def test_pattern_test_uses_model_geometry(self):
        transport = MockTransport()
        printer = PaperangP2(transport, model=MODEL_384)
        printer.print_pattern_test()

        payloads = bitmap_payloads(transport)
        assert payloads
        for payload in payloads:
            assert len(payload) % 48 == 0
            assert len(payload) <= (MAX_PACKET_DATA // 48) * 48

    def test_heat_density_test_uses_model_geometry(self):
        transport = MockTransport()
        printer = PaperangP2(transport, model=MODEL_384)
        printer.print_heat_density_test()

        payloads = bitmap_payloads(transport)
        assert payloads
        for payload in payloads:
            assert len(payload) % 48 == 0

    def test_print_image_scales_to_model_width(self):
        from PIL import Image

        src = "/tmp/paperang_test_models_image.png"
        Image.new("RGB", (100, 50), "white").save(src)

        transport = MockTransport()
        printer = PaperangP2(transport, model=MODEL_384)
        printer.print_image(src)

        total = sum(len(p) for p in bitmap_payloads(transport))
        # 100x50 scaled to 384 wide -> 192 rows of 48 bytes
        assert total == 48 * 192

    def test_print_image_scales_to_p2_width(self):
        from PIL import Image

        src = "/tmp/paperang_test_models_image_p2.png"
        Image.new("RGB", (100, 50), "white").save(src)

        transport = MockTransport()
        printer = PaperangP2(transport)
        printer.print_image(src)

        total = sum(len(p) for p in bitmap_payloads(transport))
        # 100x50 scaled to 576 wide -> 288 rows of 72 bytes
        assert total == 72 * 288
