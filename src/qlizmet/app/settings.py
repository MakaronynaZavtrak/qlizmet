"""Пользовательские настройки приложения.

Простой JSON-файл рядом с базой. Чистая стандартная библиотека — прикладной слой
не должен зависеть от Qt, поэтому ни ``QSettings``, ни реестра здесь нет.
Повреждённый или отсутствующий файл не считается ошибкой: берутся значения по
умолчанию, иначе приложение не запустилось бы из-за одной битой строки.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from qlizmet.app.paths import app_data_dir

SETTINGS_FILE = "settings.json"
DEFAULT_THEME = "dark"


@dataclass(slots=True)
class Settings:
    """Настройки пользователя."""

    theme: str = DEFAULT_THEME


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
    theme = data.get("theme")
    return Settings(theme=theme if isinstance(theme, str) else DEFAULT_THEME)


def save_settings(settings: Settings, path: Path | None = None) -> None:
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8"
    )