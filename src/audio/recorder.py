"""Microphone capture via sounddevice, written to a temporary WAV file.

The recorder runs in a non-blocking way: PortAudio invokes a callback on its
own thread, and we simply accumulate the incoming frames.  Neither this module
nor the GUI every performs blocking I/O on the UI thread.
"""

from __future__ import annotations

import tempfile
from collections import deque

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

from . import devices

_SAMPLE_RATE = 16_000
_CHANNELS = 1
_DTYPE = "int16"


class AudioRecorder:
    """Records mono audio from a selected input device into a temp .wav."""

    def __init__(self, sample_rate: int = _SAMPLE_RATE, device: int | None = None) -> None:
        self.sample_rate = sample_rate
        self.device = device
        self._stream: sd.InputStream | None = None
        self._frames: deque[np.ndarray] = deque()

    def select_device(self, index: int | None) -> None:
        """Change the input device. Ignored while recording."""
        if self.is_recording:
            return
        self.device = index

    def _callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """PortAudio thread callback: copy frames, never do anything heavy."""
        self._frames.append(indata.copy())

    @property
    def is_recording(self) -> bool:
        return self._stream is not None and self._stream.active

    def start(self) -> str | None:
        """Open the input stream and begin capturing.

        Returns a warning message if the selected device is no longer
        available (e.g. it was unplugged), in which case the system default is
        used. Returns ``None`` on a clean start.
        """
        if self.is_recording:
            return None
        self._frames.clear()

        warning = None
        selected = self.device
        if selected is not None and not any(
            d.index == selected for d in devices.list_input_devices()
        ):
            selected = None
            warning = (
                "The previously selected microphone is unavailable; " "using the system default."
            )

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=_CHANNELS,
            dtype=_DTYPE,
            callback=self._callback,
            device=selected,
        )
        self._stream.start()
        return warning

    def stop(self) -> str:
        """Stop recording, write everything to a temp .wav, and return its path."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._frames:
            raise ValueError("No audio was captured.")

        audio = np.concatenate(list(self._frames), axis=0)
        handle = tempfile.NamedTemporaryFile(delete=False, prefix="whisper_", suffix=".wav")
        handle.close()
        wavfile.write(handle.name, self.sample_rate, audio)
        return handle.name
