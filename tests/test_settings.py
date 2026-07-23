"""Тесты пользовательских настроек."""
from qlizmet.app.paths import ENV_HOME
from qlizmet.app.settings import (
    DEFAULT_THEME,
    Settings,
    load_settings,
    save_settings,
    settings_path,
)


def test_defaults_when_file_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    assert load_settings().theme == DEFAULT_THEME


def test_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    save_settings(Settings(theme="light"))
    assert load_settings().theme == "light"


def test_settings_live_in_app_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    save_settings(Settings(theme="dark"))
    assert settings_path().parent == tmp_path
    assert settings_path().exists()


def test_broken_file_falls_back(tmp_path, monkeypatch) -> None:
    """Битый файл не должен мешать запуску приложения."""
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    settings_path().write_text("{это не json", encoding="utf-8")
    assert load_settings().theme == DEFAULT_THEME


def test_wrong_shape_falls_back(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    settings_path().write_text('["список вместо объекта"]', encoding="utf-8")
    assert load_settings().theme == DEFAULT_THEME


def test_wrong_type_falls_back(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    settings_path().write_text('{"theme": 42}', encoding="utf-8")
    assert load_settings().theme == DEFAULT_THEME
