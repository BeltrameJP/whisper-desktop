"""Tests for the transcription worker in ``src.whisper_engine.engine``."""

from __future__ import annotations

from queue import Queue
from unittest.mock import MagicMock, patch

from src.whisper_engine.engine import Job, Transcription, WhisperWorker, _strip_overlap
from src.whisper_engine.settings import Settings


class _Segment:
    def __init__(self, text: str) -> None:
        self.text = text


class _Info:
    language = "en"


def _fake_model(segments: list[str]) -> MagicMock:
    model = MagicMock()
    model.transcribe.return_value = ([_Segment(s) for s in segments], _Info())
    return model


def _worker(model, settings: Settings | None = None) -> tuple[WhisperWorker, Queue, Queue]:
    jobs: Queue = Queue()
    results: Queue = Queue()
    worker = WhisperWorker(settings or Settings(), jobs, results)
    worker._model = model  # avoid loading a real model
    return worker, jobs, results


def _first_result(results: Queue) -> Transcription:
    return results.get_nowait()


# ---- overlap stripping ---------------------------------------------------
def test_strip_overlap_removes_repeated_leading_words() -> None:
    running = "hello world this is a test"
    new = "this is a test of the system"
    assert _strip_overlap(running, new) == "of the system"


def test_strip_overlap_no_match_keeps_all() -> None:
    running = "one two three"
    new = "four five"
    assert _strip_overlap(running, new) == "four five"


def test_strip_overlap_empty_running() -> None:
    assert _strip_overlap("", "hello world") == "hello world"


# ---- live chunks ---------------------------------------------------------
def test_live_chunk_uses_condition_on_previous_text() -> None:
    model = _fake_model(["hello world"])
    worker, jobs, results = _worker(model)
    worker._transcribe(Job(wav_path="chunk.wav", live=True))
    assert model.transcribe.call_args.kwargs["condition_on_previous_text"] is True


def test_live_chunk_emits_incremental_text_and_accumulates() -> None:
    model = _fake_model(["hello world"])
    worker, jobs, results = _worker(model)
    r1 = worker._transcribe(Job(wav_path="a.wav", live=True))
    assert r1.append is True
    assert r1.text == "hello world"

    model.transcribe.return_value = ([_Segment("world foo bar")], _Info())
    r2 = worker._transcribe(Job(wav_path="b.wav", live=True))
    assert r2.text == "foo bar"  # overlap "world" stripped
    assert worker._running_text == "hello world foo bar"


def test_reset_job_clears_running_text() -> None:
    model = _fake_model(["hi there"])
    worker, jobs, results = _worker(model)
    worker._transcribe(Job(wav_path="a.wav", live=True))
    assert worker._running_text == "hi there"
    jobs.put(Job(reset=True))
    jobs.put(None)  # stop sentinel
    worker.run()
    assert worker._running_text == ""


# ---- one-shot ------------------------------------------------------------
def test_one_shot_emits_full_text_and_resets_context() -> None:
    model = _fake_model(["full sentence"])
    worker, jobs, results = _worker(model)
    worker._running_text = "stale"
    r = worker._transcribe(Job(wav_path="whole.wav", live=False))
    assert r.append is False
    assert r.text == "full sentence"
    assert worker._running_text == ""
    assert "condition_on_previous_text" not in model.transcribe.call_args.kwargs


# ---- model loading -------------------------------------------------------
def test_load_model_uses_download_root(tmp_path) -> None:
    settings = Settings(model_size="base", language="pt")
    jobs: Queue = Queue()
    results: Queue = Queue()
    worker = WhisperWorker(settings, jobs, results)

    fake = MagicMock()
    with (
        patch("src.whisper_engine.engine.WhisperModel", return_value=fake) as whisper_cls,
        patch("src.whisper_engine.engine.model_download_root", return_value=tmp_path / "base"),
    ):
        loaded = worker._load_model()

    assert loaded is fake
    call = whisper_cls.call_args
    assert call.args[0] == "base"
    assert call.kwargs["download_root"] == str(tmp_path / "base")
    assert call.kwargs["device"] == "cpu"
    assert call.kwargs["compute_type"] == "int8"


# ---- errors --------------------------------------------------------------
def test_transcribe_error_returns_error_result() -> None:
    model = _fake_model([])
    model.transcribe.side_effect = RuntimeError("boom")
    worker, jobs, results = _worker(model)
    r = worker._transcribe(Job(wav_path="a.wav", live=True))
    assert r.error == "boom"
    assert r.append is True
