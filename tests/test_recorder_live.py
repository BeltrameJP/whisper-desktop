"""Tests for live chunking in ``src.audio.recorder``."""

from __future__ import annotations

import tempfile

import numpy as np
from scipy.io import wavfile

from src.audio.recorder import AudioRecorder

_SAMPLE_RATE = 16_000


def _audio(seconds: float, amp: float = 1000.0) -> np.ndarray:
    n = int(_SAMPLE_RATE * seconds)
    tone = np.sin(2 * np.pi * 440 * np.arange(n) / _SAMPLE_RATE) * amp
    return tone.astype(np.int16)


def _live_recorder(**kwargs) -> AudioRecorder:
    rec = AudioRecorder(live=True, sample_rate=_SAMPLE_RATE, **kwargs)
    handle = tempfile.NamedTemporaryFile(delete=False, prefix="whisper_live_", suffix=".raw")
    rec._raw_handle = handle
    rec._raw_path = handle.name
    return rec


# ---- chunking on silence -------------------------------------------------
def test_flushes_chunk_after_silence_gap() -> None:
    rec = _live_recorder()
    rec._process_audio(_audio(1.0))  # voice (amp 1000 > threshold 400)
    assert rec.ready_chunks.empty()
    rec._process_audio(_audio(0.4, amp=1.0))  # 4 silent blocks
    assert not rec.ready_chunks.empty()
    path = rec.ready_chunks.get_nowait()
    rate, data = wavfile.read(path)
    assert rate == _SAMPLE_RATE
    assert data.ndim == 1
    assert data.size > 0


def test_detection_runs_with_small_callback_buffers() -> None:
    rec = _live_recorder()
    frame = _audio(1.0)  # 16000 samples
    for i in range(0, len(frame), 512):  # feed 512-sample callbacks (< one block)
        rec._process_audio(frame[i : i + 512])
    rec._process_audio(_audio(0.4, amp=1.0))  # silence -> flush
    assert not rec.ready_chunks.empty()


def test_no_flush_during_continuous_voice() -> None:
    rec = _live_recorder()
    for _ in range(5):
        rec._process_audio(_audio(0.5))  # continuous loud audio
    assert rec.ready_chunks.empty()


def test_last_rms_reflects_recent_block() -> None:
    rec = _live_recorder()
    rec._process_audio(_audio(0.2, amp=1000.0))
    assert rec.last_rms > 0
    rec._process_audio(np.zeros(_SAMPLE_RATE, dtype=np.int16))
    assert rec.last_rms == 0.0


def test_flush_resets_and_can_flush_again() -> None:
    rec = _live_recorder()
    rec._process_audio(_audio(1.0))
    rec._process_audio(_audio(0.4, amp=1.0))  # first flush
    first = rec.ready_chunks.get_nowait()
    rec._process_audio(_audio(1.0))  # new voice
    rec._process_audio(_audio(0.4, amp=1.0))  # second flush
    second = rec.ready_chunks.get_nowait()
    assert first != second


# ---- RAM tail stays bounded ---------------------------------------------
def test_ram_tail_is_bounded() -> None:
    rec = _live_recorder(tail_seconds=0.5)
    for _ in range(10):
        rec._process_audio(_audio(1.0, amp=1.0))
    total = sum(f.size for f in rec._tail)
    assert total <= int(0.5 * _SAMPLE_RATE)


# ---- stop skips final chunk, returns full-session wav --------------------
def test_stop_skips_final_chunk_and_returns_full_wav() -> None:
    rec = _live_recorder()
    rec._process_audio(_audio(1.0))  # voice, no silence yet
    assert rec.ready_chunks.empty()
    path = rec.stop()
    assert rec.ready_chunks.empty()  # final partial chunk is not emitted
    assert path is not None
    rate, data = wavfile.read(path)
    assert rate == _SAMPLE_RATE
    assert data.size == int(1.0 * _SAMPLE_RATE)  # whole session, not a partial chunk
    assert rec._raw_path is None


def test_stop_returns_full_wav_in_live_mode() -> None:
    rec = _live_recorder()
    rec._process_audio(_audio(1.0))  # voice
    rec._process_audio(_audio(0.5, amp=1.0))  # silence -> chunk flush
    assert not rec.ready_chunks.empty()
    rec.ready_chunks.get_nowait()
    rec._process_audio(_audio(0.7))  # more voice after the flush
    path = rec.stop()
    assert path is not None
    rate, data = wavfile.read(path)
    assert rate == _SAMPLE_RATE
    assert data.size == int(2.2 * _SAMPLE_RATE)  # full session
    assert rec._raw_path is None


def test_stop_with_no_audio_emits_nothing() -> None:
    rec = _live_recorder()
    path = rec.stop()
    assert rec.ready_chunks.empty()
    assert path is None


def test_stop_after_silence_flush_does_not_repeat() -> None:
    rec = _live_recorder()
    rec._process_audio(_audio(1.0))
    rec._process_audio(_audio(0.4, amp=1.0))  # silence -> first flush
    assert not rec.ready_chunks.empty()
    rec.ready_chunks.get_nowait()

    rec._process_audio(_audio(1.0, amp=1.0))  # more silence after the flush
    rec.stop()  # final flush must NOT emit: no new speech since last flush
    assert rec.ready_chunks.empty()


def test_long_silence_does_not_emit_extra_chunks() -> None:
    rec = _live_recorder()
    rec._process_audio(_audio(1.0))
    rec._process_audio(_audio(0.4, amp=1.0))  # flush 1
    rec.ready_chunks.get_nowait()

    rec._process_audio(_audio(3.0, amp=1.0))  # 3s of pure silence
    assert rec.ready_chunks.empty()  # no repeated silence-driven flush


# ---- one-shot mode is unchanged ------------------------------------------
def test_one_shot_returns_full_wav_on_stop() -> None:
    rec = AudioRecorder(live=False, sample_rate=_SAMPLE_RATE)
    rec._incoming.append(_audio(1.0))
    rec._incoming.append(_audio(0.5))
    path = rec.stop()
    assert path is not None
    rate, data = wavfile.read(path)
    assert data.size == int(1.5 * _SAMPLE_RATE)


def test_one_shot_no_audio_raises() -> None:
    rec = AudioRecorder(live=False, sample_rate=_SAMPLE_RATE)
    try:
        rec.stop()
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
