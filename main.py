"""Whisper Desktop — cross-platform offline voice dictation.

Run with:  poetry run python main.py
"""

from src.audio import devices
from src.config import AppConfig
from src.gui.app import GUIApp


def _reset_unavailable_device(config: AppConfig) -> None:
    """If the saved device is no longer present, reset it to the default."""
    if config.input_device_id is None:
        return
    if not any(d.index == config.input_device_id for d in devices.list_input_devices()):
        config.input_device_id = None
        config.save()


def main() -> None:
    config = AppConfig().load()
    _reset_unavailable_device(config)
    app = GUIApp(config=config)
    app.mainloop()


if __name__ == "__main__":
    main()
