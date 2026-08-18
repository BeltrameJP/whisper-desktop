"""Tests for the on-demand model downloader (ADR 0015)."""

from __future__ import annotations

from unittest.mock import patch

from src.whisper_engine import downloader


def test_models_dir_under_cache(monkeypatch) -> None:
    monkeypatch.setattr(downloader, "user_cache_dir", lambda name: "C:/cache/whisper-desktop")
    assert downloader.models_dir() == downloader.Path("C:/cache/whisper-desktop/models")


def test_model_download_root_is_per_model(monkeypatch) -> None:
    monkeypatch.setattr(downloader, "user_cache_dir", lambda name: "C:/cache/whisper-desktop")
    root = downloader.model_download_root("base")
    assert root == downloader.Path("C:/cache/whisper-desktop/models/base")


def test_model_present_true_when_files_exist(tmp_path) -> None:
    for name in downloader._REQUIRED_FILES:
        (tmp_path / name).write_text("x", encoding="utf-8")
    with patch.object(downloader, "model_download_root", return_value=tmp_path):
        assert downloader.model_present("base") is True


def test_model_present_false_when_missing(tmp_path) -> None:
    with patch.object(downloader, "model_download_root", return_value=tmp_path):
        assert downloader.model_present("base") is False


def test_download_model_calls_snapshot_download(tmp_path) -> None:
    calls = {}

    def fake_snapshot(repo_id, **kwargs):
        calls["repo_id"] = repo_id
        calls["local_dir"] = kwargs["local_dir"]
        calls["allow_patterns"] = kwargs["allow_patterns"]
        return str(kwargs["local_dir"])

    with (
        patch.object(downloader, "model_download_root", return_value=tmp_path),
        patch.object(downloader, "snapshot_download", side_effect=fake_snapshot),
    ):
        result = downloader.download_model("base")

    assert result == tmp_path
    assert calls["repo_id"] == "Systran/faster-whisper-base"
    assert calls["local_dir"] == tmp_path
    assert "model.bin" in calls["allow_patterns"]
