"""Пользовательские настройки приложения.

Простой JSON-файл рядом с базой. Чистая стандартная библиотека — прикладной слой
не должен зависеть от Qt, поэтому ни ``QSettings``, ни реестра здесь нет.

Файл читается снисходительно: отсутствующие, лишние или испорченные поля не
считаются ошибкой, вместо них берутся значения по умолчанию. Иначе одна кривая
строка мешала бы запуску, а старый файл настроек ломался бы при каждом
добавлении новой опции.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from datetime import date
from pathlib import Path

from qlizmet.app.paths import app_data_dir

SETTINGS_FILE = "settings.json"
DEFAULT_THEME = "dark"


@dataclass(slots=True)
class Settings:
    """Настройки пользователя."""

    theme: str = DEFAULT_THEME
    reminders_enabled: bool = True
    #: Дата последнего напоминания в формате ISO; пусто — ещё не напоминали.
    last_reminder_date: str = ""
    #: Закрытие окна сворачивает приложение в трей, а не завершает его.
    minimize_to_tray: bool = True
    #: Показывали ли уже разовое пояснение про сворачивание.
    tray_notice_shown: bool = False
    #: Тихие часы: не напоминаем раньше и позже этих часов по местному времени.
    quiet_before: int = 9
    quiet_after: int = 22

    @property
    def last_reminder(self) -> date | None:
        try:
            return date.fromisoformat(self.last_reminder_date)
        except ValueError:
            return None

    def with_reminder_sent(self, moment: date) -> "Settings":
        return replace(self, last_reminder_date=moment.isoformat())

    def with_tray_notice_shown(self) -> "Settings":
        return replace(self, tray_notice_shown=True)


def settings_path() -> Path:
    return app_data_dir() / SETTINGS_FILE


def load_settings(path: Path | None = None) -> Settings:
    """Прочитать настройки. При любой проблеме вернуть значения по умолчанию."""
    target = path or settings_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Settings()
    if not isinstance(data, dict):
        return Settings()

    defaults = Settings()
    theme = data.get("theme")
    enabled = data.get("reminders_enabled")
    last = data.get("last_reminder_date")
    minimize = data.get("minimize_to_tray")
    notice = data.get("tray_notice_shown")
    before = data.get("quiet_before")
    after = data.get("quiet_after")
    return Settings(
        theme=theme if isinstance(theme, str) else defaults.theme,
        reminders_enabled=(
            enabled if isinstance(enabled, bool) else defaults.reminders_enabled
        ),
        last_reminder_date=(
            last if isinstance(last, str) else defaults.last_reminder_date
        ),
        minimize_to_tray=(
            minimize if isinstance(minimize, bool) else defaults.minimize_to_tray
        ),
        tray_notice_shown=(
            notice if isinstance(notice, bool) else defaults.tray_notice_shown
        ),
        quiet_before=_hour(before, defaults.quiet_before),
        quiet_after=_hour(after, defaults.quiet_after),
    )


def _hour(value: object, fallback: int) -> int:
    """Час суток из настроек; мусор и значения вне 0..24 заменяем умолчанием."""
    if isinstance(value, bool) or not isinstance(value, int):
        return fallback
    return value if 0 <= value <= 24 else fallback


def save_settings(settings: Settings, path: Path | None = None) -> None:
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8"
    )
