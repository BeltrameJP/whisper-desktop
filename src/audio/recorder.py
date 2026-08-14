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

_SAMPLE_RATE = 16_000
_CHANNELS = 1
_DTYPE = "int16"


class AudioRecorder:
    """Records mono audio from the default input device into a temp .wav."""

    def __init__(self, sample_rate: int = _SAMPLE_RATE) -> None:
        self.sample_rate = sample_rate
        self._stream: sd.InputStream | None = None
        self._frames: deque[np.ndarray] = deque()

    def _callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """PortAudio thread callback: copy frames, never do anything heavy."""
        self._frames.append(indata.copy())

    @property
    def is_recording(self) -> bool:
        return self._stream is not None and self._stream.active

    def start(self) -> None:
        """Open the input stream and begin capturing."""
        if self.is_recording:
            return
        self._frames.clear()
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=_CHANNELS,
            dtype=_DTYPE,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> str:
        """Stop recording, write everything to a temp .wav, and return its path."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._frames:
            raise ValueError("No audio was captured.")

        audio = np.concatenate(list(self._frames), axis=0)
        handle = tempfile.NamedTemporaryFile(
            delete=False, prefix="whisper_", suffix=".wav"
        )
        handle.close()
        wavfile.write(handle.name, self.sample_rate, audio)
        return handle.name
