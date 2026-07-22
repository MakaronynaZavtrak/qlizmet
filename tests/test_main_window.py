"""Дымовые тесты главного окна. Работают headless через offscreen-платформу."""
import pytest

pytest.importorskip("PySide6")

from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.storage.sqlite.repositories import SqliteDeckRepository  # noqa: E402
from qlizmet.ui.main_window import MainWindow  # noqa: E402


@pytest.fixture
def window(conn, qt_host) -> MainWindow:
    library = LibraryService(SqliteDeckRepository(conn))
    return MainWindow(library, parent=qt_host)


def test_main_window_title(window) -> None:
    assert window.windowTitle() == "qlizmet"


def test_main_window_has_central_widget(window) -> None:
    assert window.centralWidget() is not None


def test_main_window_shows_deck_list(window) -> None:
    assert window.deck_list is not None