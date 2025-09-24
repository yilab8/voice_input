"""Configuration utilities for the voice input application."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class WhisperConfig:
    """Configuration for the Whisper speech recognition backend."""

    model_size: str = "medium"
    compute_type: str = "auto"
    beam_size: int = 5
    language: Optional[str] = None
    download_root: Optional[Path] = None


@dataclass
class HotkeyConfig:
    """Configuration for the global hotkey."""

    hotkey: str = "ctrl+windows"
    release_timeout_s: float = 0.3
    suppress: bool = True


@dataclass
class RecordingConfig:
    """Configuration related to audio capture."""

    sample_rate: int = 16_000
    channels: int = 1
    block_size: int = 2048
    dtype: str = "int16"
    silence_timeout_s: float = 1.0


@dataclass
class AppConfig:
    """Aggregate configuration for the application."""

    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    insert_text: bool = True
    copy_to_clipboard: bool = True
    focus_active_window: bool = True

    @staticmethod
    def default() -> "AppConfig":
        """Return the default configuration."""

        return AppConfig()
