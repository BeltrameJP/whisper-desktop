"""Whisper Desktop — cross-platform offline voice dictation.

Run with:  poetry run python main.py
"""
from src.gui.app import GUIApp


def main() -> None:
    app = GUIApp()
    app.mainloop()


if __name__ == "__main__":
    main()
