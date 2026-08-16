"""Enumerate available audio input devices for the GUI.

Thin, pure wrappers around sounddevice's query APIs so the GUI never touches
PortAudio internals and the logic is unit-testable by mocking ``sounddevice``.
"""

from __future__ import annotations

from dataclasses import dataclass

import sounddevice as sd


@dataclass(frozen=True)
class InputDevice:
    """An audio input device as shown in the settings UI."""

    index: int
    name: str


def list_input_devices() -> list[InputDevice]:
    """Return all devices that can capture audio (have input channels)."""
    devices = []
    for device in sd.query_devices():
        if int(device["max_input_channels"]) > 0:
            devices.append(InputDevice(index=int(device["index"]), name=str(device["name"])))
    return devices


def grouped_input_devices() -> list[InputDevice]:
    """Return one representative device per logical mic, grouped by name.

    PortAudio often reports several entries (host-API / format variants) for a
    single physical device, so the raw enumeration can list dozens of options
    for just a few microphones.  Grouping by exact name collapses these into a
    single entry per device.  The representative entry is the one matching the
    system default if present, otherwise the lowest index in the group.
    """
    raw = list_input_devices()
    default = default_input_index()
    by_name: dict[str, list[InputDevice]] = {}
    for device in raw:
        by_name.setdefault(device.name, []).append(device)

    result: list[InputDevice] = []
    for name, group in by_name.items():
        representative = min(group, key=lambda d: (d.index != default, d.index))
        result.append(representative)
    return result


def default_input_index() -> int | None:
    """Return the index of the system's default input device, or ``None``.

    ``sd.default.device`` may be a single int, a ``_InputOutputPair`` (an
    ``(input, output)`` pair), a tuple/list, or a dict; we resolve the input
    slot defensively and return ``None`` for anything we cannot interpret.
    """
    default = sd.default.device
    if default is None:
        return None
    if isinstance(default, dict):
        default = default.get("index")
    elif isinstance(default, bool):
        return None
    elif not isinstance(default, int):
        try:
            default = default[0]
        except (IndexError, KeyError, TypeError):
            return None
    if default is None:
        return None
    try:
        return int(default)
    except (TypeError, ValueError):
        return None


def device_label(index: int | None, devices: list[InputDevice] | None = None) -> str:
    """Human-friendly label for a device index.

    ``None`` or an index equal to the default resolves to "(Default)"; unknown
    indices (e.g. a device that was unplugged) are marked as unavailable.
    """
    if index is None:
        return "(Default)"
    devices = devices if devices is not None else list_input_devices()
    for device in devices:
        if device.index == index:
            return f"{index}: {device.name}"
    return f"(Unavailable) {index}"
