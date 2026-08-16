"""Persisted user-facing application settings.

Unlike the transcription engine's ``Settings`` (a frozen, in-memory dataclass),
this module holds settings the user changes in the GUI and expects to survive
restarts.  Values are stored as JSON in the OS-appropriate user config directory
(see ADR 0008).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from platformdirs import user_config_dir

_APP_DIR = "whisper-desktop"
_CONFIG_FILE = "config.json"


@dataclass
class AppConfig:
    """User preferences persisted on disk.

    ``input_device_id`` is the integer index of the selected input device as
    reported by sounddevice, or ``None`` to use the system default.
    """

    input_device_id: int | None = None

    def _config_path(self, base_dir: str | Path | None = None) -> Path:
        base = Path(base_dir) if base_dir else Path(user_config_dir(_APP_DIR))
        return base / _CONFIG_FILE

    def load(self, base_dir: str | Path | None = None) -> "AppConfig":
        """Load settings from disk, merging any stored keys over defaults.

        Unknown or invalid values are ignored so a hand-edited or stale file
        never breaks startup.  Missing file -> defaults.
        """
        path = self._config_path(base_dir)
        if not path.exists():
            return self

        try:
            with open(path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return self

        if not isinstance(raw, dict):
            return self

        merged = asdict(self)
        for fld in fields(self):
            if fld.name not in raw or raw[fld.name] is None:
                continue
            value = raw[fld.name]
            try:
                merged[fld.name] = self._coerce(fld.type, fld.default, value)
            except (TypeError, ValueError):
                continue

        if merged["input_device_id"] is not None and merged["input_device_id"] < 0:
            merged["input_device_id"] = None

        return type(self)(**merged)

    @staticmethod
    def _coerce(annotation, default, value):
        """Coerce a raw JSON value to the field's type, using the default's type."""
        default_type = type(default)
        if default_type is not type(None):
            return default_type(value)
        # ``None`` default: guess from the annotation's non-None member.
        for member in getattr(annotation, "__args__", ()):
            if member is not type(None):
                return member(value)
        return value

    def save(self, base_dir: str | Path | None = None) -> None:
        """Persist settings to disk, creating the config directory if needed."""
        path = self._config_path(base_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(asdict(self), handle, indent=2)

    @staticmethod
    def user_config_path() -> Path:
        """The directory where settings are stored, for display in the GUI."""
        return Path(user_config_dir(_APP_DIR))
