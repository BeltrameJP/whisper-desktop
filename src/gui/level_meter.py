"""A Discord-style input-sensitivity meter.

A horizontal level bar that fills with the current input loudness and has a
draggable threshold marker. The level and the marker share a normalized 0-1
scale derived from an int16 dB scale, so the marker shows the silence threshold
relative to the live input.

The module exposes pure conversion helpers (``rms_to_level`` /
``level_to_rms``) separate from the widget so they can be unit-tested without a
Tk instance.
"""

from __future__ import annotations

import math
from tkinter import Canvas

_FULL_SCALE = 32768.0  # int16 full scale
_DB_RANGE = 60.0  # display range, -60..0 dB mapped to 0..1


def rms_to_level(rms: float) -> float:
    """Map an int16 RMS value to a normalized 0-1 level using a dB scale."""
    if rms <= 0:
        return 0.0
    db = 20.0 * math.log10(rms / _FULL_SCALE)
    db = max(-_DB_RANGE, min(0.0, db))
    return (db + _DB_RANGE) / _DB_RANGE


def level_to_rms(level: float) -> float:
    """Inverse of :func:`rms_to_level`."""
    level = max(0.0, min(1.0, level))
    db = level * _DB_RANGE - _DB_RANGE
    return _FULL_SCALE * math.pow(10.0, db / 20.0)


class LevelMeter(Canvas):
    """A level bar with a draggable silence-threshold marker.

    ``on_change(level)`` is invoked while the marker is dragged so the caller
    can apply the new threshold live.
    """

    def __init__(
        self,
        master,
        width: int = 320,
        height: int = 24,
        threshold: float = 0.5,
        on_change=None,
    ) -> None:
        super().__init__(master, width=width, height=height, bg="gray16", highlightthickness=0)
        self._width = width
        self._height = height
        self._level = 0.0
        self._threshold = max(0.0, min(1.0, threshold))
        self._on_change = on_change

        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_click)
        self._redraw()

    # ---- public API ------------------------------------------------------
    def set_level(self, level: float) -> None:
        """Set the current input level (0-1) and redraw the fill."""
        self._level = max(0.0, min(1.0, level))
        self._redraw()

    def set_threshold(self, level: float) -> None:
        self._threshold = max(0.0, min(1.0, level))
        self._redraw()

    @property
    def threshold(self) -> float:
        return self._threshold

    # ---- interaction ------------------------------------------------------
    def _on_click(self, event) -> None:
        level = max(0.0, min(1.0, event.x / self._width))
        self._threshold = level
        self._redraw()
        if self._on_change is not None:
            self._on_change(level)

    # ---- drawing ----------------------------------------------------------
    def _redraw(self) -> None:
        self.delete("all")
        margin = 2
        y = margin
        h = self._height - 2 * margin
        bar_w = self._width - 2 * margin

        # track
        self.create_rectangle(margin, y, margin + bar_w, y + h, fill="#3a3a3a", outline="")

        # fill (current level)
        fill_w = int(bar_w * self._level)
        if fill_w > 0:
            color = "#2ecc71" if self._level >= self._threshold else "#7f8c8d"
            self.create_rectangle(margin, y, margin + fill_w, y + h, fill=color, outline="")

        # threshold marker
        mx = margin + int(bar_w * self._threshold)
        self.create_line(mx, y, mx, y + h, fill="#ffffff", width=2)
        self.create_rectangle(mx - 3, y - 1, mx + 3, y + h + 1, fill="#ffffff", outline="")
