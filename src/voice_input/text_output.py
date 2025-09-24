"""Helpers for injecting recognised text into the operating system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from .window import ActiveWindow, ActiveWindowTracker

try:  # pragma: no cover
    import keyboard  # type: ignore
except Exception as exc:  # pragma: no cover
    keyboard = None  # type: ignore
    _KEYBOARD_IMPORT_ERROR = exc
else:  # pragma: no cover
    _KEYBOARD_IMPORT_ERROR = None

try:  # pragma: no cover
    import pyperclip  # type: ignore
except Exception as exc:  # pragma: no cover
    pyperclip = None  # type: ignore
    _CLIPBOARD_IMPORT_ERROR = exc
else:  # pragma: no cover
    _CLIPBOARD_IMPORT_ERROR = None


@dataclass
class TextEmitter:
    """Insert recognised text via keyboard events or clipboard."""

    insert_text: bool = True
    copy_to_clipboard: bool = True
    paste_hotkey: str = "ctrl+v"
    keyboard_module: Optional[object] = None
    clipboard_module: Optional[object] = None
    window_tracker: Optional["ActiveWindowTracker"] = None

    def __post_init__(self) -> None:
        if self.keyboard_module is None:
            self.keyboard_module = keyboard
        if self.clipboard_module is None:
            self.clipboard_module = pyperclip

    def emit(self, text: str, *, target_window: Optional["ActiveWindow"] = None) -> None:
        """Send *text* to the operating system."""

        if not text:
            return

        if self.copy_to_clipboard:
            self._copy_to_clipboard(text)

        if self.insert_text:
            self._focus_window(target_window)
            self._insert_text(text)

    def _copy_to_clipboard(self, text: str) -> None:
        module = self.clipboard_module
        if module is None:
            raise RuntimeError("pyperclip is required to copy text to the clipboard") from _CLIPBOARD_IMPORT_ERROR
        if not hasattr(module, "copy"):
            raise RuntimeError("Clipboard module does not provide a copy() function")
        module.copy(text)

    def _insert_text(self, text: str) -> None:
        module = self.keyboard_module
        if module is None:
            raise RuntimeError("keyboard is required to send key events") from _KEYBOARD_IMPORT_ERROR
        if self.copy_to_clipboard and hasattr(module, "send"):
            module.send(self.paste_hotkey)
        elif hasattr(module, "write"):
            module.write(text)
        else:
            raise RuntimeError("Keyboard module must provide send() or write()")

    def _focus_window(self, target_window: Optional["ActiveWindow"]) -> None:
        if target_window is None:
            return
        tracker = self.window_tracker
        if tracker is None:
            return
        tracker.focus(target_window)


__all__ = ["TextEmitter"]
