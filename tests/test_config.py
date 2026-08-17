"""Tests for the persisted app settings in ``src.config``."""

from __future__ import annotations

import json

from src.config import AppConfig


def test_defaults_when_no_file(tmp_path) -> None:
    config = AppConfig().load(tmp_path)
    assert config.input_device_id is None
    assert config.live_mode is True
    assert config.live_threshold == 0.25


def test_live_threshold_round_trip(tmp_path) -> None:
    AppConfig(live_threshold=0.3).save(tmp_path)
    loaded = AppConfig().load(tmp_path)
    assert loaded.live_threshold == 0.3


def test_live_threshold_clamped_to_range(tmp_path) -> None:
    (tmp_path / "config.json").write_text(json.dumps({"live_threshold": 1.7}), encoding="utf-8")
    assert AppConfig().load(tmp_path).live_threshold == 1.0
    (tmp_path / "config.json").write_text(json.dumps({"live_threshold": -0.4}), encoding="utf-8")
    assert AppConfig().load(tmp_path).live_threshold == 0.0


def test_round_trip(tmp_path) -> None:
    config = AppConfig(input_device_id=3)
    config.save(tmp_path)
    loaded = AppConfig().load(tmp_path)
    assert loaded.input_device_id == 3


def test_live_mode_round_trip_false(tmp_path) -> None:
    AppConfig(live_mode=False).save(tmp_path)
    loaded = AppConfig().load(tmp_path)
    assert loaded.live_mode is False


def test_live_mode_null_falls_back_to_default(tmp_path) -> None:
    (tmp_path / "config.json").write_text(json.dumps({"live_mode": None}), encoding="utf-8")
    loaded = AppConfig().load(tmp_path)
    assert loaded.live_mode is True


def test_live_mode_string_false_is_false(tmp_path) -> None:
    (tmp_path / "config.json").write_text(json.dumps({"live_mode": "false"}), encoding="utf-8")
    loaded = AppConfig().load(tmp_path)
    assert loaded.live_mode is False


def test_missing_file_returns_defaults(tmp_path) -> None:
    loaded = AppConfig(input_device_id=7).load(tmp_path)
    assert loaded.input_device_id == 7


def test_unknown_keys_are_ignored(tmp_path) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps({"input_device_id": 2, "future_option": True}),
        encoding="utf-8",
    )
    loaded = AppConfig().load(tmp_path)
    assert loaded.input_device_id == 2


def test_invalid_negative_device_is_none(tmp_path) -> None:
    (tmp_path / "config.json").write_text(json.dumps({"input_device_id": -1}), encoding="utf-8")
    loaded = AppConfig().load(tmp_path)
    assert loaded.input_device_id is None


def test_corrupt_file_falls_back_to_defaults(tmp_path) -> None:
    (tmp_path / "config.json").write_text("{not valid json", encoding="utf-8")
    loaded = AppConfig(input_device_id=5).load(tmp_path)
    assert loaded.input_device_id == 5


def test_save_creates_config_dir(tmp_path) -> None:
    nested = tmp_path / "a" / "b"
    AppConfig(input_device_id=1).save(nested)
    assert (nested / "config.json").exists()
    assert json.loads((nested / "config.json").read_text(encoding="utf-8"))["input_device_id"] == 1
