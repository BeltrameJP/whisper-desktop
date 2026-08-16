"""Tests for microphone selection in ``src.audio.recorder``."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.audio import devices
from src.audio.recorder import AudioRecorder


class _FakeStream:
    active = True

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def close(self) -> None:
        pass


def _input_stream_factory(*_args, **_kwargs):
    return _FakeStream()


@patch.object(devices, "list_input_devices", return_value=[])
@patch.object(devices.sd, "InputStream", side_effect=_input_stream_factory)
def test_start_no_device_uses_default(mock_stream, _) -> None:
    recorder = AudioRecorder(device=None)
    recorder.start()
    assert mock_stream.call_args.kwargs["device"] is None


@patch.object(devices, "list_input_devices")
@patch.object(devices.sd, "InputStream", side_effect=_input_stream_factory)
def test_start_passes_selected_device(mock_stream, mock_list) -> None:
    mock_list.return_value = [devices.InputDevice(index=2, name="Yeti")]
    recorder = AudioRecorder(device=2)
    recorder.start()
    assert mock_stream.call_args.kwargs["device"] == 2


@patch.object(devices, "list_input_devices")
@patch.object(devices.sd, "InputStream", side_effect=_input_stream_factory)
def test_start_stale_device_falls_back_with_warning(mock_stream, mock_list) -> None:
    mock_list.return_value = [devices.InputDevice(index=0, name="Mic")]
    recorder = AudioRecorder(device=9)
    warning = recorder.start()
    assert mock_stream.call_args.kwargs["device"] is None
    assert warning is not None
    assert "unavailable" in warning


@patch.object(devices, "list_input_devices")
@patch.object(devices.sd, "InputStream", side_effect=_input_stream_factory)
def test_select_device_ignored_while_recording(mock_stream, mock_list) -> None:
    mock_list.return_value = [devices.InputDevice(index=0, name="Mic")]
    recorder = AudioRecorder(device=0)
    recorder._stream = MagicMock(active=True)
    recorder.select_device(5)
    assert recorder.device == 0
