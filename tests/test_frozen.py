"""Тесты поведения в собранном приложении.

Собранное приложение отличается от запуска из исходников одним важным местом:
``sys.executable`` там — это сам qlizmet, а не интерпретатор. От этого зависит
команда автозапуска, и ошибиться тут дорого: неверная запись в автозагрузке
молча не сработает при следующем входе в систему.
"""
from unittest.mock import patch

from qlizmet.app import autostart as autostart_module
from qlizmet.app.autostart import DesktopEntryAutostart, launch_command
from qlizmet.app.paths import is_frozen


def test_not_frozen_when_running_from_sources() -> None:
    assert is_frozen() is False


def test_command_from_sources_uses_module() -> None:
    assert "-m qlizmet" in launch_command()


def test_command_when_frozen_is_the_executable_itself() -> None:
    """В сборке добавлять «-m qlizmet» нельзя: такого модуля рядом с exe нет."""
    with patch.object(autostart_module, "is_frozen", return_value=True), patch.object(
        autostart_module.sys, "executable", "/opt/qlizmet/qlizmet"
    ):
        command = launch_command()

    assert command == "/opt/qlizmet/qlizmet"
    assert "-m" not in command


def test_frozen_command_is_quoted_when_path_has_spaces() -> None:
    """Путь вида «C:\\Program Files\\...» обязан пережить запись в автозапуск."""
    with patch.object(autostart_module, "is_frozen", return_value=True), patch.object(
        autostart_module.sys, "executable", "/opt/my apps/qlizmet"
    ):
        command = launch_command()

    assert command != "/opt/my apps/qlizmet"  # закавычено
    assert "my apps" in command


def test_autostart_entry_uses_frozen_command(tmp_path) -> None:
    with patch.object(autostart_module, "is_frozen", return_value=True), patch.object(
        autostart_module.sys, "executable", "/opt/qlizmet/qlizmet"
    ):
        autostart = DesktopEntryAutostart(tmp_path)
        autostart.enable()

    text = autostart.path.read_text(encoding="utf-8")
    assert "Exec=/opt/qlizmet/qlizmet" in text
    assert "-m qlizmet" not in text
