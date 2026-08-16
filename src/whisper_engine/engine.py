"""Background thread that transcribes WAV files with faster-whisper.

The GUI communicates with this worker through two queues:
  * ``jobs``   -- the GUI pushes a WAV file path (or ``None`` to stop).
  * ``results`` -- the worker pushes back a ``Transcription`` namedtuple.

The model is loaded lazily on the first transcription so the window opens fast.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from queue import Queue

from faster_whisper import WhisperModel

from .settings import Settings


@dataclass
class Transcription:
    text: str
    language: str | None
    elapsed_seconds: float
    error: str | None = None


class WhisperWorker(threading.Thread):
    """Consumes WAV paths from ``jobs`` and emits results to ``results``."""

    def __init__(
        self, settings: Settings, jobs: "Queue[str | None]", results: "Queue[Transcription]"
    ) -> None:
        super().__init__(daemon=True)
        self.settings = settings
        self.jobs = jobs
        self.results = results
        self._model: WhisperModel | None = None

    def _load_model(self) -> WhisperModel:
        """Load (and cache) the model on first use."""
        if self._model is None:
            self._model = WhisperModel(
                self.settings.model_size,
                device=self.settings.device,
                compute_type=self.settings.compute_type,
            )
        return self._model

    def run(self) -> None:
        while True:
            path = self.jobs.get()
            if path is None:
                break  # stop sentinel
            self.results.put(self._transcribe(path))

    def _transcribe(self, wav_path: str) -> Transcription:
        started = time.monotonic()
        try:
            model = self._load_model()
            segments, info = model.transcribe(
                wav_path, language=self.settings.language, beam_size=self.settings.beam_size
            )
            text = "".join(segment.text for segment in segments).strip()
            return Transcription(
                text=text,
                language=info.language,
                elapsed_seconds=round(time.monotonic() - started, 2),
            )
        except Exception as exc:  # surface errors to the GUI
            return Transcription(
                text="",
                language=None,
                elapsed_seconds=round(time.monotonic() - started, 2),
                error=str(exc),
            )
        finally:
            self._cleanup(wav_path)

    @staticmethod
    def _cleanup(wav_path: str) -> None:
        """Always delete the temporary WAV after transcription."""
        try:
            os.remove(wav_path)
        except OSError:
            pass
