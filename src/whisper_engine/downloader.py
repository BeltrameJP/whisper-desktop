"""On-demand download of Whisper models into the app cache (ADR 0015).

Models live under ``platformdirs.user_cache_dir("whisper-desktop")/models``,
one subdirectory per model size, so the downloader and the engine share a
single consistent location (ADR 0008) and ``base`` / ``base.en`` never collide.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from huggingface_hub import snapshot_download
from platformdirs import user_cache_dir
from tqdm import tqdm

_APP_DIR = "whisper-desktop"
_REPO_PREFIX = "Systran/faster-whisper"

# Required files that mark a model as fully downloaded. Mirrors the patterns
# used by ``faster_whisper.utils.download_model``.
_REQUIRED_FILES = (
    "model.bin",
    "config.json",
    "tokenizer.json",
)


def models_dir() -> Path:
    """The root cache directory holding all downloaded models."""
    return Path(user_cache_dir(_APP_DIR)) / "models"


def model_download_root(model_size: str) -> Path:
    """Per-model directory under the cache root."""
    return models_dir() / model_size


def model_present(model_size: str) -> bool:
    """True if the model's required files already exist locally."""
    root = model_download_root(model_size)
    return all((root / name).is_file() for name in _REQUIRED_FILES)


def _progress_tqdm(progress: Callable[[int, int], None] | None) -> type:
    """A tqdm subclass that forwards ``(done_bytes, total_bytes)`` to ``progress``.

    ``snapshot_download`` instantiates the class internally and accepts no
    constructor args, so the callback is bound through a closure.
    """

    class _Progress(tqdm):
        def update(self, n: int = 1) -> None:
            super().update(n)
            if progress is not None:
                progress(int(self.n), int(self.total or self.n))

    return _Progress


def download_model(
    model_size: str,
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    """Download ``model_size`` into the cache, reporting ``(done, total)`` bytes.

    Returns the path to the downloaded model directory. The call blocks until
    the download finishes, so it must be run off the GUI thread.
    """
    root = model_download_root(model_size)
    snapshot_download(
        repo_id=f"{_REPO_PREFIX}-{model_size}",
        local_dir=root,
        local_dir_use_symlinks=False,
        allow_patterns=[
            "config.json",
            "preprocessor_config.json",
            "model.bin",
            "tokenizer.json",
            "vocabulary.*",
        ],
        tqdm_class=_progress_tqdm(progress),
    )
    return root
