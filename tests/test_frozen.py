"""Тесты поведения в собранном приложении.

Собранное приложение отличается от запуска из исходников двумя важными
мелочами. Во-первых, ``sys.executable`` там — это сам qlizmet, а не
интерпретатор. Во-вторых, система запускает его с признаком автозапуска, по
которому приложение стартует сразу в трей.

Ошибка в любой из этих мелочей проявится не сразу: неверная запись в
автозагрузке молча не сработает при следующем входе в систему.
"""
from unittest.mock import patch

from qlizmet.app import autostart as autostart_module
from qlizmet.app.autostart import (
    STARTUP_FLAG,
    DesktopEntryAutostart,
    launch_command,
    quote_path,
    should_start_hidden,
)
from qlizmet.app.paths import is_frozen


# --- режим сборки ---


def test_not_frozen_when_running_from_sources() -> None:
    assert is_frozen() is False


def test_command_from_sources_uses_module() -> None:
    assert "-m qlizmet" in launch_command()


def test_command_when_frozen_points_at_executable(tmp_path) -> None:
    """В сборке добавлять «-m qlizmet» нельзя: такого модуля рядом с exe нет."""
    with patch.object(autostart_module, "is_frozen", return_value=True), patch.object(
        autostart_module.sys, "executable", "/opt/qlizmet/qlizmet"
    ):
        command = launch_command()

    assert command.startswith("/opt/qlizmet/qlizmet")
    assert "-m qlizmet" not in command


def test_command_carries_startup_flag() -> None:
    """Иначе при каждом включении компьютера окно лезло бы на экран."""
    assert STARTUP_FLAG in launch_command()


# --- кавычки по правилам системы ---


def test_windows_path_uses_double_quotes() -> None:
    """Одинарные кавычки Windows не понимает, а «Program Files» есть у всех."""
    with patch.object(autostart_module.sys, "platform", "win32"):
        quoted = quote_path(r"C:\Program Files\qlizmet\qlizmet.exe")

    assert quoted.startswith('"')
    assert quoted.endswith('"')
    assert "'" not in quoted


def test_windows_path_without_spaces_is_left_alone() -> None:
    with patch.object(autostart_module.sys, "platform", "win32"):
        assert quote_path(r"C:\qlizmet\qlizmet.exe") == r"C:\qlizmet\qlizmet.exe"


def test_posix_path_with_spaces_is_quoted() -> None:
    with patch.object(autostart_module.sys, "platform", "linux"):
        quoted = quote_path("/opt/my apps/qlizmet")

    assert quoted != "/opt/my apps/qlizmet"
    assert "my apps" in quoted


# --- запуск системой ---


def test_hidden_start_requires_flag() -> None:
    assert should_start_hidden([STARTUP_FLAG], tray_available=True)
    assert not should_start_hidden([], tray_available=True)


def test_no_hidden_start_without_tray() -> None:
    """Без трея спрятанное окно означало бы недоступное приложение."""
    assert not should_start_hidden([STARTUP_FLAG], tray_available=False)


# --- запись автозапуска ---


def test_autostart_entry_uses_frozen_command(tmp_path) -> None:
    with patch.object(autostart_module, "is_frozen", return_value=True), patch.object(
        autostart_module.sys, "executable", "/opt/qlizmet/qlizmet"
    ):
        autostart = DesktopEntryAutostart(tmp_path)
        autostart.enable()

    text = autostart.path.read_text(encoding="utf-8")
    assert "Exec=/opt/qlizmet/qlizmet" in text
    assert STARTUP_FLAG in text
    assert "-m qlizmet" not in text
