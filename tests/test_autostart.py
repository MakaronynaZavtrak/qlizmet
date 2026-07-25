"""Тесты автозапуска: команда запуска, флаг ``--startup`` и файлы автозапуска.

Тесты платформо-независимы: где поведение зависит от ОС, платформа и признак
собранной сборки подменяются через ``monkeypatch``. Так набор одинаково зелёный
и в Linux-CI, и на машине разработчика под Windows.
"""
import sys

from qlizmet.app import autostart
from qlizmet.app.autostart import (
    STARTUP_FLAG,
    DesktopEntryAutostart,
    LaunchAgentAutostart,
    launch_command,
    quote_path,
    should_start_hidden,
)

# Путь без пробелов: quote_path не трогает его ни на одной платформе,
# поэтому итог launch_command детерминирован независимо от хоста.
EXE = "/opt/qlizmet/qlizmet"


def test_launch_command_from_source(monkeypatch) -> None:
    """Из исходников нужен интерпретатор с модулем ``-m qlizmet``."""
    monkeypatch.setattr(autostart, "is_frozen", lambda: False)
    monkeypatch.setattr(sys, "executable", EXE)
    assert launch_command() == f"{EXE} -m qlizmet {STARTUP_FLAG}"


def test_launch_command_frozen(monkeypatch) -> None:
    """В собранной сборке ``sys.executable`` — сам qlizmet, без ``-m``."""
    monkeypatch.setattr(autostart, "is_frozen", lambda: True)
    monkeypatch.setattr(sys, "executable", EXE)
    assert launch_command() == f"{EXE} {STARTUP_FLAG}"


def test_launch_command_frozen_has_no_module_flag(monkeypatch) -> None:
    """Регрессия: в frozen-команде не должно быть ссылки на модуль ``-m``.

    Именно ``-m qlizmet`` в собранной сборке указывал бы на несуществующий
    модуль и ломал автозапуск.
    """
    monkeypatch.setattr(autostart, "is_frozen", lambda: True)
    monkeypatch.setattr(sys, "executable", EXE)
    command = launch_command()
    assert "-m" not in command.split()
    assert "qlizmet" not in command.split()[1:]  # только флаг после пути


def test_startup_flag_hides_window_when_tray_present() -> None:
    assert should_start_hidden([STARTUP_FLAG], tray_available=True) is True


def test_startup_flag_ignored_without_tray() -> None:
    """Без трея прятать нельзя: приложение стало бы невидимым и недоступным."""
    assert should_start_hidden([STARTUP_FLAG], tray_available=False) is False


def test_no_flag_shows_window() -> None:
    assert should_start_hidden([], tray_available=True) is False


def test_unrelated_args_do_not_trigger_hidden() -> None:
    assert should_start_hidden(["--verbose"], tray_available=True) is False


def test_quote_path_posix_quotes_spaces(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert quote_path("/home/me/qlizmet app/q") == "'/home/me/qlizmet app/q'"


def test_quote_path_windows_quotes_spaces(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    assert quote_path(r"C:\Program Files\qlizmet\q.exe") == '"C:\\Program Files\\qlizmet\\q.exe"'


def test_quote_path_windows_no_spaces_unchanged(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    assert quote_path(r"C:\qlizmet\q.exe") == r"C:\qlizmet\q.exe"


def test_desktop_entry_writes_command_and_toggles(tmp_path) -> None:
    """Linux: команда попадает в ``Exec=``, а enable/disable создаёт и удаляет файл."""
    entry = DesktopEntryAutostart(tmp_path, command=f"{EXE} {STARTUP_FLAG}")
    assert entry.is_enabled() is False

    entry.enable()
    assert entry.is_enabled() is True
    content = entry.path.read_text(encoding="utf-8")
    assert f"Exec={EXE} {STARTUP_FLAG}" in content
    assert entry.path.suffix == ".desktop"

    entry.disable()
    assert entry.is_enabled() is False


def test_launch_agent_splits_command_into_arguments(tmp_path) -> None:
    """macOS: команда раскладывается по ``ProgramArguments`` пословно."""
    agent = LaunchAgentAutostart(tmp_path, command=f"{EXE} {STARTUP_FLAG}")
    agent.enable()

    content = agent.path.read_text(encoding="utf-8")
    assert f"<string>{EXE}</string>" in content
    assert f"<string>{STARTUP_FLAG}</string>" in content
    assert agent.path.name == "com.qlizmet.plist"

    agent.disable()
    assert agent.is_enabled() is False
