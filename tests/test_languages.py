"""Tests for language handling and model auto-selection (ADR 0015)."""

from __future__ import annotations

from src.whisper_engine.languages import (
    LANGUAGES,
    language_options,
    model_for_language,
)


def test_languages_cover_whisper_set() -> None:
    assert "en" in LANGUAGES
    assert "pt" in LANGUAGES
    assert "ja" in LANGUAGES
    assert len(LANGUAGES) >= 99


def test_model_for_language_auto_uses_base_en() -> None:
    assert model_for_language(None) == "base.en"


def test_model_for_language_english_uses_base_en() -> None:
    assert model_for_language("en") == "base.en"


def test_model_for_language_other_uses_base() -> None:
    assert model_for_language("pt") == "base"
    assert model_for_language("ja") == "base"


def test_language_options_include_auto_first() -> None:
    options = language_options()
    assert options[0] == (None, "Auto")
    assert all(isinstance(code, str) for code, _ in options[1:])
    assert all("(" in label and label.endswith(")") for _, label in options[1:])


def test_language_options_label_has_name_and_code() -> None:
    options = language_options()
    pt = next(code for code, _ in options if code == "pt")
    label = next(label for code, label in options if code == "pt")
    assert pt == "pt"
    assert label == "Portuguese (pt)"
