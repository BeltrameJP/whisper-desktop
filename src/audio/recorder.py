"""Microphone capture via sounddevice, written to temporary audio files.

The recorder runs in a non-blocking way: PortAudio invokes a callback on its
own thread, and we simply accumulate the incoming frames. Neither this module
nor the GUI ever performs blocking I/O on the UI thread.

Two modes are supported:

* **Live** (default): audio is streamed to a growing raw-PCM temp file on disk
  and chunked into WAV files by a dedicated "pump" thread as soon as a silence
  gap is detected. Finished chunk paths are queued on ``ready_chunks`` so the
  GUI can hand them to the transcription worker while recording continues.
  Memory stays flat because only a short rolling tail is held in RAM. On
  ``stop()`` the whole session is written to a single WAV (returned) so the GUI
  can run a final full-context re-transcription.
* **One-shot**: the whole recording is buffered and written to a single WAV
  when ``stop()`` is called (transcribe-on-stop behavior).
"""

from __future__ import annotations

import os
import queue
import tempfile
import threading
from collections import deque

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

from . import devices

_SAMPLE_RATE = 16_000
_CHANNELS = 1
_DTYPE = "int16"

_BLOCK_SECONDS = 0.1  # energy is measured per ~100ms block
_SILENCE_MS = 300
_ENERGY_THRESHOLD = 400.0  # RMS amplitude of an int16 block
_OVERLAP_SECONDS = 0.75
_TAIL_SECONDS = 2.0
_MIN_CHUNK_SECONDS = 0.2


class AudioRecorder:
    """Records mono audio from a selected input device into temp audio files."""

    def __init__(
        self,
        sample_rate: int = _SAMPLE_RATE,
        device: int | None = None,
        live: bool = True,
        energy_threshold: float = _ENERGY_THRESHOLD,
        silence_ms: int = _SILENCE_MS,
        overlap_seconds: float = _OVERLAP_SECONDS,
        tail_seconds: float = _TAIL_SECONDS,
        block_seconds: float = _BLOCK_SECONDS,
    ) -> None:
        self.sample_rate = sample_rate
        self.device = device
        self.live = live

        self.energy_threshold = energy_threshold
        self._block_frames = max(1, int(sample_rate * block_seconds))
        self._silence_blocks = max(1, round(silence_ms / (block_seconds * 1000)))
        self._overlap_frames = int(sample_rate * overlap_seconds)
        self._tail_frames = int(sample_rate * tail_seconds)
        self._min_chunk_frames = int(sample_rate * _MIN_CHUNK_SECONDS)

        self._stream: sd.InputStream | None = None
        self._incoming: deque[np.ndarray] = deque()
        self._ready_chunks: "queue.Queue[str]" = queue.Queue()

        self._pump: threading.Thread | None = None
        self._stop_event: threading.Event | None = None
        self._raw_path: str | None = None
        self._raw_handle = None
        self._total_frames = 0
        self._last_flush = 0
        self._silent_run = 0
        self._since_flush_has_speech = False
        self._tail: deque[np.ndarray] = deque()
        self._pending: np.ndarray | None = None

        self._monitor: sd.InputStream | None = None
        self._current_rms = 0.0

    def select_device(self, index: int | None) -> None:
        """Change the input device. Ignored while recording."""
        if self.is_recording:
            return
        self.device = index

    def _callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """PortAudio thread callback: copy frames, never do anything heavy."""
        self._incoming.append(indata.copy())

    @property
    def is_recording(self) -> bool:
        return self._stream is not None and self._stream.active

    @property
    def ready_chunks(self) -> "queue.Queue[str]":
        """Completed chunk WAV paths, produced in live mode."""
        return self._ready_chunks

    @property
    def last_rms(self) -> float:
        """The most recent input-block RMS, for the GUI level meter."""
        return self._current_rms

    @property
    def is_monitoring(self) -> bool:
        return self._monitor is not None and self._monitor.active

    def monitor(self) -> None:
        """Open a lightweight stream that only measures input level.

        Used by the Settings dialog to feed a live level meter without
        recording. Does not write to disk or run the pump.
        """
        if self.is_monitoring or self.is_recording:
            return
        self._current_rms = 0.0
        self._monitor = sd.InputStream(
            samplerate=self.sample_rate,
            channels=_CHANNELS,
            dtype=_DTYPE,
            callback=self._monitor_callback,
            device=self.device,
        )
        self._monitor.start()

    def stop_monitor(self) -> None:
        if self._monitor is not None:
            self._monitor.stop()
            self._monitor.close()
            self._monitor = None

    def _monitor_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        self._current_rms = self._rms(indata)

    # ---- capture lifecycle -------------------------------------------------
    def start(self) -> str | None:
        """Open the input stream and begin capturing.

        Returns a warning message if the selected device is no longer
        available (e.g. it was unplugged), in which case the system default is
        used. Returns ``None`` on a clean start.
        """
        if self.is_recording:
            return None
        self._incoming.clear()
        self._tail.clear()
        self._total_frames = 0
        self._last_flush = 0
        self._silent_run = 0
        self._since_flush_has_speech = False
        self._pending = None

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

        if self.live:
            self._raw_handle = tempfile.NamedTemporaryFile(
                delete=False, prefix="whisper_live_", suffix=".raw"
            )
            self._raw_path = self._raw_handle.name
            self._stop_event = threading.Event()
            self._pump = threading.Thread(target=self._pump_loop, daemon=True)
            self._pump.start()

        return warning

    def stop(self) -> str | None:
        """Stop recording and finalize audio.

        In both modes the whole session is written to a temp WAV whose path is
        returned (``None`` only if no audio was captured in live mode). In live
        mode the pump is signalled to drain remaining frames and exit; the final
        partial chunk is **not** emitted — the full-session WAV is what gets
        transcribed on Stop.
        """
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self.live:
            if not self._incoming:
                raise ValueError("No audio was captured.")
            audio = np.concatenate(list(self._incoming), axis=0)
            handle = tempfile.NamedTemporaryFile(delete=False, prefix="whisper_", suffix=".wav")
            handle.close()
            wavfile.write(handle.name, self.sample_rate, audio)
            return handle.name

        if self._pump is not None:
            self._stop_event.set()
            self._pump.join(timeout=5)
            self._pump = None

        if self._raw_handle is not None:
            self._raw_handle.close()
            self._raw_handle = None
        full_path = None
        if self._raw_path is not None:
            full_path = self._write_full_wav()
            try:
                os.remove(self._raw_path)
            except OSError:
                pass
            self._raw_path = None
        return full_path

    # ---- live pump thread --------------------------------------------------
    def _pump_loop(self) -> None:
        """Consume frames, chunk on silence, and exit once stopped."""
        while True:
            self._drain_incoming()
            if self._stop_event.is_set():
                self._drain_incoming()  # drain remaining frames into the raw file
                return
            self._stop_event.wait(0.02)

    def _write_full_wav(self) -> str | None:
        """Write the whole session's raw PCM as a WAV; returns its path."""
        if self._total_frames == 0:
            return None
        data = np.fromfile(self._raw_path, dtype=_DTYPE, count=self._total_frames)
        handle = tempfile.NamedTemporaryFile(delete=False, prefix="whisper_full_", suffix=".wav")
        handle.close()
        wavfile.write(handle.name, self.sample_rate, data)
        return handle.name

    def _drain_incoming(self) -> None:
        while self._incoming:
            self._process_audio(self._incoming.popleft())

    def _process_audio(self, frames: np.ndarray) -> None:
        """Append frames to disk/tail and flush a chunk if a silence gap ends."""
        frames = np.asarray(frames).reshape(-1).astype(_DTYPE)
        if frames.size == 0:
            return

        self._raw_handle.write(frames.tobytes())
        self._raw_handle.flush()
        self._total_frames += frames.size

        self._tail.append(frames)
        while sum(f.size for f in self._tail) > self._tail_frames:
            self._tail.popleft()

        self._current_rms = self._rms(frames)

        # Accumulate across callbacks so detection runs on full blocks even when
        # the device delivers buffers smaller than one block. Leftover samples
        # (< one block) carry into the next callback.
        self._pending = (
            frames if self._pending is None else np.concatenate([self._pending, frames])
        )
        while self._pending.size >= self._block_frames:
            block = self._pending[: self._block_frames]
            self._pending = self._pending[self._block_frames :]
            if self._rms(block) < self.energy_threshold:
                self._silent_run += 1
            else:
                self._silent_run = 0
                self._since_flush_has_speech = True
            if self._silent_run >= self._silence_blocks:
                self._flush_chunk()

    @staticmethod
    def _rms(block: np.ndarray) -> float:
        return float(np.sqrt(np.mean(block.astype(np.float64) ** 2)))

    def _flush_chunk(self) -> None:
        """Emit the current chunk (with overlap) as a WAV on ``ready_chunks``.

        Only flushes when there is real new speech since the last flush; pure
        silence or overlap alone never emits a chunk.
        """
        self._silent_run = 0
        if not self._since_flush_has_speech:
            return
        if self._total_frames - self._last_flush < self._min_chunk_frames:
            return

        start = max(0, self._last_flush - self._overlap_frames)
        end = self._total_frames
        chunk = np.fromfile(self._raw_path, dtype=_DTYPE, count=end - start, offset=start * 2)
        handle = tempfile.NamedTemporaryFile(delete=False, prefix="whisper_live_", suffix=".wav")
        handle.close()
        wavfile.write(handle.name, self.sample_rate, chunk)
        self._ready_chunks.put(handle.name)
        self._since_flush_has_speech = False
        self._last_flush = end
