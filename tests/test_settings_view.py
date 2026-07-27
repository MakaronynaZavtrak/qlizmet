"""Тесты автозапуска и экрана настроек.

Автозапуск трогает систему пользователя, поэтому проверяется во временной папке:
все реализации принимают путь снаружи именно ради этого.
"""
import sys

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from PySide6.QtCore import QTime  # noqa: E402

from qlizmet.app.autostart import (  # noqa: E402
    DesktopEntryAutostart,
    LaunchAgentAutostart,
    launch_command,
)
from qlizmet.app.autostart import create as create_autostart  # noqa: E402
from qlizmet.app.paths import ENV_HOME  # noqa: E402
from qlizmet.app.settings import Settings, load_settings, save_settings  # noqa: E402
from qlizmet.ui.views.settings_view import (  # noqa: E402
    NO_AUTOSTART_HINT,
    NO_TRAY_HINT,
    SettingsView,
)


# --- автозапуск ---


def test_launch_command_mentions_module() -> None:
    assert "-m qlizmet" in launch_command()


def test_desktop_entry_lifecycle(tmp_path) -> None:
    autostart = DesktopEntryAutostart(tmp_path)
    assert not autostart.is_enabled()

    autostart.enable()
    assert autostart.is_enabled()
    assert autostart.path.exists()

    autostart.disable()
    assert not autostart.is_enabled()


def test_desktop_entry_contents(tmp_path) -> None:
    autostart = DesktopEntryAutostart(tmp_path, command="/usr/bin/python -m qlizmet")
    autostart.enable()

    text = autostart.path.read_text(encoding="utf-8")
    assert "[Desktop Entry]" in text
    assert "Exec=/usr/bin/python -m qlizmet" in text


def test_desktop_entry_disable_is_idempotent(tmp_path) -> None:
    """Выключение того, что и так выключено, не должно падать."""
    autostart = DesktopEntryAutostart(tmp_path)
    autostart.disable()
    autostart.disable()


def test_desktop_entry_creates_missing_directory(tmp_path) -> None:
    autostart = DesktopEntryAutostart(tmp_path / "нет" / "такой" / "папки")
    autostart.enable()
    assert autostart.is_enabled()


def test_launch_agent_lifecycle(tmp_path) -> None:
    autostart = LaunchAgentAutostart(tmp_path, command="/usr/bin/python -m qlizmet")
    autostart.enable()

    text = autostart.path.read_text(encoding="utf-8")
    assert "RunAtLoad" in text
    assert "<string>/usr/bin/python</string>" in text

    autostart.disable()
    assert not autostart.is_enabled()


def test_create_matches_platform() -> None:
    manager = create_autostart()
    if sys.platform.startswith(("win", "linux")) or sys.platform == "darwin":
        assert manager is not None
    else:
        assert manager is None


# --- экран настроек ---


class FakeAutostart:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def is_enabled(self) -> bool:
        return self.enabled

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    return tmp_path


def _view(qt_host, *, autostart=None, tray_available=True) -> SettingsView:
    return SettingsView(
        autostart=autostart, tray_available=tray_available, parent=qt_host
    )


def test_shows_saved_settings(home, qt_host) -> None:
    save_settings(
        Settings(reminders_enabled=False, quiet_before=7 * 60, quiet_after=23 * 60)
    )
    view = _view(qt_host)

    assert not view.findChild(object, "remindersCheck").isChecked()
    assert view.findChild(object, "quietBefore").time() == QTime(7, 0)
    assert view.findChild(object, "quietAfter").time() == QTime(23, 0)


def test_toggle_is_saved_immediately(home, qt_host) -> None:
    """Кнопки «Применить» нет — значит изменение должно сохраняться сразу."""
    view = _view(qt_host)
    view.findChild(object, "remindersCheck").setChecked(False)

    assert load_settings().reminders_enabled is False


def test_quiet_hours_are_saved(home, qt_host) -> None:
    view = _view(qt_host)
    view.findChild(object, "quietBefore").setTime(QTime(6, 30))  # с минутами

    assert load_settings().quiet_before == 6 * 60 + 30


def test_loading_does_not_resave(home, qt_host) -> None:
    """Показ настроек не должен считаться их изменением."""
    save_settings(Settings(theme="light", tray_notice_shown=True))
    view = _view(qt_host)
    view.reload()

    stored = load_settings()
    assert stored.theme == "light"
    assert stored.tray_notice_shown is True


def test_change_emits_signal(home, qt_host) -> None:
    view = _view(qt_host)
    seen = []
    view.settings_changed.connect(seen.append)

    view.findChild(object, "remindersCheck").setChecked(False)
    assert len(seen) == 1
    assert seen[0].reminders_enabled is False


def test_autostart_checkbox_reflects_state(home, qt_host) -> None:
    view = _view(qt_host, autostart=FakeAutostart(enabled=True))
    assert view.findChild(object, "autostartCheck").isChecked()


def test_autostart_toggle_calls_system(home, qt_host) -> None:
    manager = FakeAutostart()
    view = _view(qt_host, autostart=manager)

    view.findChild(object, "autostartCheck").setChecked(True)
    assert manager.enabled is True

    view.findChild(object, "autostartCheck").setChecked(False)
    assert manager.enabled is False


def test_autostart_disabled_when_unsupported(home, qt_host) -> None:
    view = _view(qt_host, autostart=None)
    assert not view.findChild(object, "autostartCheck").isEnabled()
    assert view.hint_text() == NO_AUTOSTART_HINT


def test_tray_toggle_disabled_without_tray(home, qt_host) -> None:
    view = _view(qt_host, tray_available=False)
    assert not view.findChild(object, "trayCheck").isEnabled()
    assert view.hint_text() == NO_TRAY_HINT


def test_settings_screen_is_reachable(conn, qt_host, home) -> None:
    from qlizmet.app.deck_service import DeckService
    from qlizmet.app.library_service import LibraryService
    from qlizmet.storage.sqlite.repositories import SqliteDeckRepository
    from qlizmet.ui.main_window import PAGE_SETTINGS, MainWindow

    repo = SqliteDeckRepository(conn)
    window = MainWindow(LibraryService(repo), DeckService(repo), parent=qt_host)
    window.deck_list.settings_requested.emit()

    assert window.current_page() == PAGE_SETTINGS
