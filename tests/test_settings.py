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


# --- напоминания в настройках ---


def test_reminder_defaults(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    settings = load_settings()
    assert settings.reminders_enabled is True
    assert settings.last_reminder is None


def test_reminder_date_roundtrip(tmp_path, monkeypatch) -> None:
    from datetime import date

    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    save_settings(Settings().with_reminder_sent(date(2026, 1, 10)))
    assert load_settings().last_reminder == date(2026, 1, 10)


def test_broken_reminder_date_is_ignored(tmp_path, monkeypatch) -> None:
    """Испорченная дата не должна ронять запуск — просто считаем, что не напоминали."""
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    save_settings(Settings(last_reminder_date="позавчера"))
    assert load_settings().last_reminder is None


def test_old_settings_file_still_loads(tmp_path, monkeypatch) -> None:
    """Файл, записанный прошлой версией, не должен ломаться из-за новых полей."""
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    settings_path().write_text('{"theme": "light"}', encoding="utf-8")

    settings = load_settings()
    assert settings.theme == "light"
    assert settings.reminders_enabled is True


def test_wrong_type_for_flag_falls_back(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    settings_path().write_text('{"reminders_enabled": "да"}', encoding="utf-8")
    assert load_settings().reminders_enabled is True


def test_with_reminder_sent_keeps_other_fields() -> None:
    from datetime import date

    original = Settings(theme="light", reminders_enabled=False)
    updated = original.with_reminder_sent(date(2026, 1, 10))
    assert updated.theme == "light"
    assert updated.reminders_enabled is False


def test_legacy_hours_migrate_to_minutes(tmp_path, monkeypatch) -> None:
    """Старый файл (тихие часы в часах, без schema) переводится в минуты."""
    import json

    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"quiet_before": 9, "quiet_after": 22}), encoding="utf-8"
    )
    settings = load_settings()
    assert settings.quiet_before == 9 * 60
    assert settings.quiet_after == 22 * 60


def test_saved_minutes_do_not_migrate_again(tmp_path, monkeypatch) -> None:
    """Сохранённые минуты (со schema) не умножаются на 60 при следующем чтении."""
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    save_settings(Settings(quiet_before=9 * 60 + 15, quiet_after=21 * 60 + 45))
    reloaded = load_settings()
    assert reloaded.quiet_before == 9 * 60 + 15
    assert reloaded.quiet_after == 21 * 60 + 45

    save_settings(reloaded)  # ещё один круг — по-прежнему минуты
    assert load_settings().quiet_before == 9 * 60 + 15
