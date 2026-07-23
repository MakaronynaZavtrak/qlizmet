"""Где приложение хранит свои данные.

База и медиафайлы лежат в пользовательской папке приложения, а не рядом с кодом:
Windows — ``%APPDATA%\\qlizmet``, macOS — ``~/Library/Application Support/qlizmet``,
Linux — ``$XDG_DATA_HOME/qlizmet`` (по умолчанию ``~/.local/share/qlizmet``).

Переменная окружения ``QLIZMET_HOME`` перекрывает выбор — этим пользуются тесты,
чтобы не трогать реальные данные пользователя.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ENV_HOME = "QLIZMET_HOME"
APP_DIR_NAME = "qlizmet"
DATABASE_NAME = "qlizmet.db"
MEDIA_DIR_NAME = "media"


def app_data_dir() -> Path:
    """Папка с данными приложения (создаётся при необходимости)."""
    override = os.environ.get(ENV_HOME)
    if override:
        path = Path(override)
    elif sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
        path = Path(base) / APP_DIR_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
        path = Path(base) / APP_DIR_NAME

    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    """Путь к файлу базы."""
    return app_data_dir() / DATABASE_NAME


def media_dir() -> Path:
    """Папка с картинками карточек (создаётся при необходимости)."""
    path = app_data_dir() / MEDIA_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path