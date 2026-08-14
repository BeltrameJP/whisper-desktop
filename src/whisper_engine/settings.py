"""Runtime configuration for the transcription engine."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Tunable options for faster-whisper.

    ``model_size`` examples: ``tiny``, ``tiny.en``, ``base``, ``base.en``,
    ``small``, ``medium``, ``large-v3``.
    """

    model_size: str = "base.en"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str | None = None  # None => auto-detect; "en" => force English
    beam_size: int = 5
