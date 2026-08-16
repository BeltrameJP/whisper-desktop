"""Tests for input device enumeration in ``src.audio.devices``."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.audio import devices


def _fake_device(index, name, in_ch, out_ch=0):
    return {
        "index": index,
        "name": name,
        "max_input_channels": in_ch,
        "max_output_channels": out_ch,
    }


@patch.object(devices.sd, "query_devices")
def test_list_input_devices_filters_inputs(mock_query) -> None:
    mock_query.return_value = [
        _fake_device(0, "Mic", 1),
        _fake_device(1, "Speakers", 0, out_ch=2),
        _fake_device(2, "Stereo Mic", 2),
    ]
    result = devices.list_input_devices()
    assert [(d.index, d.name) for d in result] == [
        (0, "Mic"),
        (2, "Stereo Mic"),
    ]


@patch.object(devices.sd, "query_devices")
def test_list_input_devices_empty(mock_query) -> None:
    mock_query.return_value = []
    assert devices.list_input_devices() == []


def test_grouped_input_devices_merges_same_name_lowest_index() -> None:
    with patch.object(
        devices.sd,
        "query_devices",
        return_value=[
            _fake_device(0, "Yeti", 1),
            _fake_device(3, "Yeti", 1),
            _fake_device(4, "Yeti", 1),
        ],
    ):
        with patch.object(devices.sd, "default", MagicMock(device=None)):
            result = devices.grouped_input_devices()
    assert [(d.index, d.name) for d in result] == [(0, "Yeti")]


def test_grouped_input_devices_prefers_default_index() -> None:
    with patch.object(
        devices.sd,
        "query_devices",
        return_value=[
            _fake_device(0, "Yeti", 1),
            _fake_device(3, "Yeti", 1),
        ],
    ):
        with patch.object(devices.sd, "default", MagicMock(device=3)):
            result = devices.grouped_input_devices()
    assert [(d.index, d.name) for d in result] == [(3, "Yeti")]


def test_grouped_input_devices_keeps_distinct_names() -> None:
    with patch.object(
        devices.sd,
        "query_devices",
        return_value=[
            _fake_device(0, "Yeti", 1),
            _fake_device(1, "Webcam", 1),
            _fake_device(5, "Yeti", 1),
        ],
    ):
        with patch.object(devices.sd, "default", MagicMock(device=None)):
            result = devices.grouped_input_devices()
    assert [(d.index, d.name) for d in result] == [(0, "Yeti"), (1, "Webcam")]


def test_grouped_input_devices_empty() -> None:
    with patch.object(devices.sd, "query_devices", return_value=[]):
        with patch.object(devices.sd, "default", MagicMock(device=None)):
            assert devices.grouped_input_devices() == []


def test_grouped_input_devices_exact_name_match() -> None:
    with patch.object(
        devices.sd,
        "query_devices",
        return_value=[
            _fake_device(0, "Mic", 1),
            _fake_device(2, "mic", 1),
        ],
    ):
        with patch.object(devices.sd, "default", MagicMock(device=None)):
            result = devices.grouped_input_devices()
    assert [(d.index, d.name) for d in result] == [(0, "Mic"), (2, "mic")]


def test_default_input_index_int() -> None:
    with patch.object(devices.sd, "default", MagicMock()) as default:
        default.device = 4
        assert devices.default_input_index() == 4


def test_default_input_index_tuple() -> None:
    with patch.object(devices.sd, "default", MagicMock()) as default:
        default.device = (3, 6)
        assert devices.default_input_index() == 3


def test_default_input_index_pair_object() -> None:
    with patch.object(devices.sd, "default", MagicMock()) as default:
        pair = MagicMock()
        pair.__getitem__.side_effect = lambda key: 3 if key == 0 else 6
        default.device = pair
        assert devices.default_input_index() == 3


def test_default_input_index_bool_none() -> None:
    with patch.object(devices.sd, "default", MagicMock()) as default:
        default.device = True
        assert devices.default_input_index() is None


def test_default_input_index_unindexable_none() -> None:
    with patch.object(devices.sd, "default", MagicMock()) as default:
        default.device = object()
        assert devices.default_input_index() is None


def test_default_input_index_none() -> None:
    with patch.object(devices.sd, "default", MagicMock()) as default:
        default.device = None
        assert devices.default_input_index() is None


def test_device_label_default_when_none() -> None:
    assert devices.device_label(None) == "(Default)"


def test_device_label_known_device() -> None:
    devs = [devices.InputDevice(index=1, name="Yeti")]
    assert devices.device_label(1, devs) == "1: Yeti"


def test_device_label_unavailable() -> None:
    devs = [devices.InputDevice(index=0, name="Yeti")]
    assert devices.device_label(5, devs) == "(Unavailable) 5"
