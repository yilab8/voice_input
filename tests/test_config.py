from voice_input import AppConfig


def test_default_config():
    config = AppConfig.default()
    assert config.whisper.model_size == "medium"
    assert config.hotkey.hotkey == "ctrl+windows"
    assert config.recording.sample_rate == 16_000
    assert config.focus_active_window is True
