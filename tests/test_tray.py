"""Тесты трея: подписи, сворачивание вместо выхода, счётчик.

Настоящий системный трей в headless-среде недоступен, поэтому в окно
подставляется заглушка. Так проверяется именно наше поведение, а не Qt.
"""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from PySide6.QtGui import QCloseEvent  # noqa: E402

from qlizmet.app.deck_service import DeckService  # noqa: E402
from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.app.scheduler_service import SchedulerService  # noqa: E402
from qlizmet.core.srs import PendingCounts  # noqa: E402
from qlizmet.storage.sqlite.repositories import (  # noqa: E402
    SqliteDeckRepository,
    SqliteProgressRepository,
)
from qlizmet.ui import tray as tray_module  # noqa: E402
from qlizmet.ui.main_window import MainWindow  # noqa: E402


class FakeTray:
    """Заглушка вместо системного трея."""

    def __init__(self) -> None:
        self.pending: PendingCounts | None = None
        self.hidden_notices = 0
        self.icon_refreshes = 0

    def set_pending(self, pending: PendingCounts) -> None:
        self.pending = pending

    def notify_hidden(self) -> None:
        self.hidden_notices += 1

    def refresh_icon(self) -> None:
        self.icon_refreshes += 1


@pytest.fixture
def env(conn):
    decks = SqliteDeckRepository(conn)
    progress = SqliteProgressRepository(conn)
    return (
        LibraryService(decks),
        DeckService(decks),
        SchedulerService(decks, progress),
    )


def _window(env, qt_host, *, tray=None, minimize=False) -> MainWindow:
    library, decks, scheduler = env
    return MainWindow(
        library,
        decks,
        scheduler=scheduler,
        tray=tray,
        minimize_to_tray=minimize,
        parent=qt_host,
    )


# --- подписи (чистые функции) ---


def test_label_when_nothing_pending() -> None:
    assert "всё повторено" in tray_module.pending_label(PendingCounts())


def test_label_agrees_with_number() -> None:
    assert tray_module.pending_label(PendingCounts(due=1)).endswith("1 карточка")
    assert tray_module.pending_label(PendingCounts(due=3)).endswith("3 карточки")
    assert tray_module.pending_label(PendingCounts(due=7)).endswith("7 карточек")


def test_label_sums_reviews_and_new() -> None:
    assert "5" in tray_module.pending_label(PendingCounts(due=3, new=2))


def test_tooltip_mentions_app() -> None:
    assert tray_module.tray_tooltip(PendingCounts()).startswith("qlizmet")


def test_availability_check_does_not_crash(qt_app) -> None:
    """В headless-среде трея нет — и это законное состояние."""
    assert isinstance(tray_module.is_available(), bool)


def test_availability_is_false_without_application() -> None:
    """Проверка до создания QApplication не должна ронять процесс."""
    from unittest.mock import patch

    with patch.object(tray_module.QApplication, "instance", return_value=None):
        assert tray_module.is_available() is False
        assert tray_module.create() is None


def test_create_returns_none_without_tray(qt_app) -> None:
    if tray_module.is_available():
        pytest.skip("в этой среде трей доступен")
    assert tray_module.create() is None


# --- поведение окна ---


def test_without_tray_close_really_closes(env, qt_host) -> None:
    window = _window(env, qt_host)
    assert not window.minimizes_to_tray

    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()


def test_minimize_disabled_by_setting(env, qt_host) -> None:
    """Трей есть, но человек попросил закрывать по-настоящему."""
    window = _window(env, qt_host, tray=FakeTray(), minimize=False)
    assert not window.minimizes_to_tray

    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()


def test_close_hides_window_when_minimizing(env, qt_host) -> None:
    tray = FakeTray()
    window = _window(env, qt_host, tray=tray, minimize=True)
    window.show()

    event = QCloseEvent()
    window.closeEvent(event)

    assert not event.isAccepted()  # выход отменён
    assert window.isHidden()


def test_first_hide_explains_itself(env, qt_host) -> None:
    """Иначе человек решит, что программа закрылась или зависла."""
    tray = FakeTray()
    window = _window(env, qt_host, tray=tray, minimize=True)

    window.closeEvent(QCloseEvent())
    assert tray.hidden_notices == 1


def test_notice_is_shown_only_once(env, qt_host) -> None:
    tray = FakeTray()
    window = _window(env, qt_host, tray=tray, minimize=True)

    window.closeEvent(QCloseEvent())
    window.closeEvent(QCloseEvent())
    window.closeEvent(QCloseEvent())
    assert tray.hidden_notices == 1


def test_notice_can_be_suppressed_from_settings(env, qt_host) -> None:
    """Пояснение уже показывали в прошлый запуск — повторять не нужно."""
    tray = FakeTray()
    window = _window(env, qt_host, tray=tray, minimize=True)
    window.set_tray_notice_pending(False)

    window.closeEvent(QCloseEvent())
    assert tray.hidden_notices == 0


def test_notice_emits_signal_to_remember(env, qt_host) -> None:
    tray = FakeTray()
    window = _window(env, qt_host, tray=tray, minimize=True)
    seen: list[bool] = []
    window.tray_notice_shown.connect(lambda: seen.append(True))

    window.closeEvent(QCloseEvent())
    assert seen == [True]


def test_restore_shows_window_again(env, qt_host) -> None:
    tray = FakeTray()
    window = _window(env, qt_host, tray=tray, minimize=True)
    window.show()
    window.closeEvent(QCloseEvent())
    assert window.isHidden()

    window.restore_from_tray()
    assert not window.isHidden()


# --- счётчик в трее ---


def test_tray_pending_reflects_decks(env, qt_host) -> None:
    library, _, _ = env
    library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")

    tray = FakeTray()
    window = _window(env, qt_host, tray=tray, minimize=True)
    window.update_tray_pending()

    assert tray.pending.total == 2


def test_tray_pending_is_safe_without_tray(env, qt_host) -> None:
    window = _window(env, qt_host)
    window.update_tray_pending()  # не должно падать


def test_theme_change_refreshes_tray_icon(env, qt_host, tmp_path, monkeypatch) -> None:
    from qlizmet.app.paths import ENV_HOME

    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    tray = FakeTray()
    window = _window(env, qt_host, tray=tray, minimize=True)

    window.toggle_theme()
    assert tray.icon_refreshes == 1


# --- настройка применяется сразу, а не после перезапуска ---


def test_unchecking_setting_stops_minimizing(env, qt_host, tmp_path, monkeypatch) -> None:
    """Снял галочку — крестик снова закрывает приложение, без перезапуска."""
    from qlizmet.app.paths import ENV_HOME

    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    tray = FakeTray()
    window = _window(env, qt_host, tray=tray, minimize=True)
    assert window.minimizes_to_tray

    window.settings_view.findChild(object, "trayCheck").setChecked(False)

    assert not window.minimizes_to_tray
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()


def test_checking_setting_starts_minimizing(env, qt_host, tmp_path, monkeypatch) -> None:
    from qlizmet.app.paths import ENV_HOME
    from qlizmet.app.settings import Settings, save_settings

    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    save_settings(Settings(minimize_to_tray=False))  # исходно выключено
    tray = FakeTray()
    window = _window(env, qt_host, tray=tray, minimize=False)
    assert not window.minimizes_to_tray

    window.settings_view.findChild(object, "trayCheck").setChecked(True)

    assert window.minimizes_to_tray
    event = QCloseEvent()
    window.closeEvent(event)
    assert not event.isAccepted()  # свернулись, а не закрылись


def test_setting_cannot_enable_minimizing_without_tray(env, qt_host, tmp_path, monkeypatch) -> None:
    """Без трея сворачивать некуда, сколько галочку ни ставь."""
    from qlizmet.app.paths import ENV_HOME

    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    window = _window(env, qt_host, tray=None, minimize=False)
    window.set_minimize_to_tray(True)

    assert not window.minimizes_to_tray
