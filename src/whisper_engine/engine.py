"""Background thread that transcribes WAV files with faster-whisper.

The GUI communicates with this worker through two queues:
  * ``jobs``   -- the GUI pushes ``Job`` items (or ``None`` to stop).
  * ``results`` -- the worker pushes back a ``Transcription`` namedtuple.

The worker supports two modes:

* **Live** (``Job(live=True)``): a chunk of a running recording. The chunk is
  transcribed with ``condition_on_previous_text`` and the newly decoded text is
  emitted incrementally (``Transcription.append=True``), with duplicate leading
  words from the chunk overlap stripped against the running transcript. The GUI
  appends these to the textbox.
* **One-shot** (``Job(live=False)``): a whole recording transcribed at once,
  emitted as full text (``append=False``); the GUI replaces the textbox.
* **Refine** (``Job(live=False, refine=True)``): a full-session re-transcription
  requested on Stop in live mode. Uses a higher beam size so the final result is
  better refined than the streaming chunks it replaces.

The model is loaded lazily on the first transcription so the window opens fast.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from queue import Queue

from faster_whisper import WhisperModel

from .downloader import model_download_root
from .settings import Settings

_REFINE_BEAM_SIZE = 8


@dataclass(frozen=True)
class Job:
    """A unit of work for the worker.

    ``live`` marks an incremental chunk of a live session; a ``reset`` job
    (``wav_path is None``) clears the worker's running-transcript state without
    transcribing anything. ``refine`` marks a full-session re-transcription
    (higher beam size) requested on Stop.
    """

    wav_path: str | None = None
    live: bool = False
    reset: bool = False
    refine: bool = False


@dataclass
class Transcription:
    text: str
    language: str | None
    elapsed_seconds: float
    append: bool = False
    error: str | None = None


def _strip_overlap(running_text: str, new_text: str) -> str:
    """Remove the duplicated leading words of ``new_text`` that overlap the tail.

    Live chunks carry ~0.75s of the previous chunk so mid-word cuts and boundary
    tokens don't break the transcript; that overlap shows up as repeated leading
    words here, which we discard.
    """
    running_tokens = running_text.split()
    new_tokens = new_text.split()
    if not running_tokens or not new_tokens:
        return new_text

    max_k = min(len(running_tokens), len(new_tokens))
    for k in range(max_k, 0, -1):
        if running_tokens[-k:] == new_tokens[:k]:
            return " ".join(new_tokens[k:])
    return new_text


class WhisperWorker(threading.Thread):
    """Consumes ``Job`` items from ``jobs`` and emits results to ``results``."""

    def __init__(
        self, settings: Settings, jobs: "Queue[Job | None]", results: "Queue[Transcription]"
    ) -> None:
        super().__init__(daemon=True)
        self.settings = settings
        self.jobs = jobs
        self.results = results
        self._model: WhisperModel | None = None
        self._running_text = ""

    def _load_model(self) -> WhisperModel:
        """Load (and cache) the model on first use."""
        if self._model is None:
            self._model = WhisperModel(
                self.settings.model_size,
                device=self.settings.device,
                compute_type=self.settings.compute_type,
                download_root=str(model_download_root(self.settings.model_size)),
            )
        return self._model

    def run(self) -> None:
        while True:
            job = self.jobs.get()
            if job is None:
                break  # stop sentinel
            if job.reset:
                self._running_text = ""
                continue
            self.results.put(self._transcribe(job))

    def _transcribe(self, job: Job) -> Transcription:
        started = time.monotonic()
        try:
            model = self._load_model()
            if job.live:
                return self._transcribe_chunk(model, job.wav_path, started)
            return self._transcribe_full(model, job, started)
        except Exception as exc:  # surface errors to the GUI
            return Transcription(
                text="",
                language=None,
                elapsed_seconds=round(time.monotonic() - started, 2),
                append=job.live,
                error=str(exc),
            )
        finally:
            self._cleanup(job.wav_path)

    def _transcribe_chunk(
        self, model: WhisperModel, wav_path: str, started: float
    ) -> Transcription:
        """Transcribe a live chunk, dedup overlap, and emit only new text."""
        segments, info = model.transcribe(
            wav_path,
            language=self.settings.language,
            beam_size=self.settings.beam_size,
            condition_on_previous_text=True,
        )
        raw = "".join(segment.text for segment in segments).strip()
        new_text = _strip_overlap(self._running_text, raw)
        self._running_text = (self._running_text + " " + new_text).strip()
        return Transcription(
            text=new_text,
            language=info.language,
            elapsed_seconds=round(time.monotonic() - started, 2),
            append=True,
        )

    def _transcribe_full(self, model: WhisperModel, job: Job, started: float) -> Transcription:
        """Transcribe a whole recording at once; resets running context.

        A ``refine`` job uses a higher beam size for a better final result,
        since the user accepts the extra wait on Stop.
        """
        beam_size = _REFINE_BEAM_SIZE if job.refine else self.settings.beam_size
        segments, info = model.transcribe(
            job.wav_path, language=self.settings.language, beam_size=beam_size
        )
        text = "".join(segment.text for segment in segments).strip()
        self._running_text = ""
        return Transcription(
            text=text,
            language=info.language,
            elapsed_seconds=round(time.monotonic() - started, 2),
        )

    @staticmethod
    def _cleanup(wav_path: str | None) -> None:
        """Always delete the temporary WAV after transcription."""
        if wav_path is None:
            return
        try:
            os.remove(wav_path)
        except OSError:
            pass
