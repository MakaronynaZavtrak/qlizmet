"""Автозапуск приложения при входе в систему.

Единственное место в проекте, где поведение зависит от операционной системы:
Windows хранит список автозапуска в реестре, Linux — в ``~/.config/autostart``,
macOS — в ``~/Library/LaunchAgents``. Различия спрятаны за общим интерфейсом,
чтобы остальной код о них не знал.

Все реализации принимают путь (или ключ) снаружи — так их можно проверить
тестами во временной папке, не трогая настоящую систему пользователя.
"""
from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import Protocol

from qlizmet.app.paths import is_frozen

APP_ID = "qlizmet"
APP_NAME = "qlizmet"


def launch_command() -> str:
    """Команда, которой система должна запускать приложение.

    В собранном приложении ``sys.executable`` — это сам qlizmet, и добавлять
    ``-m qlizmet`` нельзя: получилась бы ссылка на несуществующий модуль.
    Из исходников же нужен интерпретатор с модулем.
    """
    if is_frozen():
        return shlex.quote(sys.executable)
    return f"{shlex.quote(sys.executable)} -m qlizmet"


class Autostart(Protocol):
    """Управление автозапуском."""

    def is_enabled(self) -> bool: ...

    def enable(self) -> None: ...

    def disable(self) -> None: ...


class DesktopEntryAutostart:
    """Linux: файл ``.desktop`` в каталоге автозапуска."""

    def __init__(self, directory: Path, command: str | None = None) -> None:
        self._path = Path(directory) / f"{APP_ID}.desktop"
        self._command = command or launch_command()

    @property
    def path(self) -> Path:
        return self._path

    def is_enabled(self) -> bool:
        return self._path.exists()

    def enable(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={APP_NAME}\n"
            f"Exec={self._command}\n"
            "Terminal=false\n"
            "X-GNOME-Autostart-enabled=true\n",
            encoding="utf-8",
        )

    def disable(self) -> None:
        self._path.unlink(missing_ok=True)


class LaunchAgentAutostart:
    """macOS: property list в ``~/Library/LaunchAgents``."""

    def __init__(self, directory: Path, command: str | None = None) -> None:
        self._path = Path(directory) / f"com.{APP_ID}.plist"
        self._command = command or launch_command()

    @property
    def path(self) -> Path:
        return self._path

    def is_enabled(self) -> bool:
        return self._path.exists()

    def enable(self) -> None:
        arguments = "".join(
            f"        <string>{part}</string>\n" for part in shlex.split(self._command)
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n'
            "<dict>\n"
            "    <key>Label</key>\n"
            f"    <string>com.{APP_ID}</string>\n"
            "    <key>ProgramArguments</key>\n"
            f"    <array>\n{arguments}    </array>\n"
            "    <key>RunAtLoad</key>\n"
            "    <true/>\n"
            "</dict>\n"
            "</plist>\n",
            encoding="utf-8",
        )

    def disable(self) -> None:
        self._path.unlink(missing_ok=True)


class RegistryAutostart:
    """Windows: значение в ветке реестра ``...\\CurrentVersion\\Run``."""

    KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

    def __init__(self, command: str | None = None) -> None:
        self._command = command or launch_command()

    def is_enabled(self) -> bool:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.KEY) as key:
                winreg.QueryValueEx(key, APP_ID)
        except OSError:
            return False
        return True

    def enable(self) -> None:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.KEY) as key:
            winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, self._command)

    def disable(self) -> None:
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self.KEY, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.DeleteValue(key, APP_ID)
        except OSError:
            pass  # записи и так не было


def create() -> Autostart | None:
    """Управление автозапуском для текущей системы или ``None``, если её не знаем."""
    if sys.platform.startswith("win"):
        return RegistryAutostart()
    if sys.platform == "darwin":
        return LaunchAgentAutostart(Path.home() / "Library" / "LaunchAgents")
    if sys.platform.startswith("linux"):
        return DesktopEntryAutostart(Path.home() / ".config" / "autostart")
    return None
