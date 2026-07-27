"""Сочетание «закрыть окно» (Cmd+W на macOS, Ctrl+W на Windows/Linux)."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from PySide6.QtGui import QKeySequence, QShortcut  # noqa: E402

from qlizmet.app.deck_service import DeckService  # noqa: E402
from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.app.scheduler_service import SchedulerService  # noqa: E402
from qlizmet.storage.sqlite.repositories import (  # noqa: E402
    SqliteDeckRepository,
    SqliteProgressRepository,
)
from qlizmet.ui.main_window import MainWindow  # noqa: E402


@pytest.fixture
def env(conn):
    decks = SqliteDeckRepository(conn)
    progress = SqliteProgressRepository(conn)
    return LibraryService(decks), DeckService(decks), SchedulerService(decks, progress)


def _close_shortcut(window: MainWindow) -> QShortcut | None:
    close = QKeySequence(QKeySequence.StandardKey.Close)  # нужен живой QApplication
    for shortcut in window.findChildren(QShortcut):
        if shortcut.key() == close:
            return shortcut
    return None


def test_close_shortcut_registered(env, qt_host) -> None:
    library, decks, scheduler = env
    window = MainWindow(library, decks, scheduler=scheduler, parent=qt_host)
    assert _close_shortcut(window) is not None  # Cmd+W / Ctrl+W повешен


def test_close_shortcut_closes_window(env, qt_host) -> None:
    library, decks, scheduler = env
    window = MainWindow(library, decks, scheduler=scheduler)  # top-level, без трея
    window.show()
    assert window.isVisible()

    _close_shortcut(window).activated.emit()  # как нажатие Cmd+W

    assert not window.isVisible()  # окно закрылось через closeEvent
