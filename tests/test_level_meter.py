"""Tests for the input-sensitivity level meter in ``src.gui.level_meter``."""

from __future__ import annotations

import math
import tkinter as tk

import pytest

from src.gui.level_meter import LevelMeter, level_to_rms, rms_to_level


# ---- dB conversion helpers ----------------------------------------------
def test_rms_to_level_monotonic_and_ranges() -> None:
    assert rms_to_level(0) == 0.0
    assert rms_to_level(32768) == 1.0
    assert rms_to_level(-5) == 0.0  # negative/zero clamped
    levels = [rms_to_level(x) for x in (10, 100, 1000, 10000, 30000)]
    assert levels == sorted(levels)


def test_level_to_rms_inverse() -> None:
    for level in (0.0, 0.1, 0.3, 0.5, 0.9, 1.0):
        rms = level_to_rms(level)
        assert math.isclose(rms_to_level(rms), level, rel_tol=1e-6)
    assert level_to_rms(2.0) == 32768  # clamped to 1.0
    assert level_to_rms(-1.0) == 32768 * 10 ** (-60 / 20)  # clamped to 0.0 -> -60dB floor


# ---- widget behaviour ----------------------------------------------------
def test_widget_threshold_drag_updates_and_fires_callback() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        changes = []
        meter = LevelMeter(root, width=320, height=26, threshold=0.5, on_change=changes.append)
        assert meter.threshold == 0.5
        meter._on_click(type("E", (), {"x": 160}))
        assert meter.threshold == pytest.approx(0.5)
        meter._on_click(type("E", (), {"x": 0}))
        assert meter.threshold == 0.0
        meter._on_click(type("E", (), {"x": 3200}))  # out of range
        assert meter.threshold == 1.0
        assert changes[-1] == 1.0
    finally:
        root.destroy()


def test_widget_set_level_does_not_move_threshold() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        meter = LevelMeter(root, width=320, height=26, threshold=0.4)
        meter.set_level(0.8)
        assert meter.threshold == 0.4
    finally:
        root.destroy()
