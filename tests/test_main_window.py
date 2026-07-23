"""Тесты главного окна и навигации между экранами (headless)."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from qlizmet.app.deck_service import DeckService  # noqa: E402
from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.storage.sqlite.repositories import SqliteDeckRepository  # noqa: E402
from qlizmet.ui.main_window import PAGE_DECK, PAGE_DECK_LIST, MainWindow  # noqa: E402
from qlizmet.ui.widgets.list_delegate import SUBTITLE_ROLE  # noqa: E402


@pytest.fixture
def library(conn) -> LibraryService:
    return LibraryService(SqliteDeckRepository(conn))


@pytest.fixture
def window(conn, qt_host) -> MainWindow:
    repo = SqliteDeckRepository(conn)
    return MainWindow(LibraryService(repo), DeckService(repo), parent=qt_host)


def test_window_title(window) -> None:
    assert window.windowTitle() == "qlizmet"


def test_window_has_central_widget(window) -> None:
    assert window.centralWidget() is not None


def test_starts_on_deck_list(window) -> None:
    assert window.current_page() == PAGE_DECK_LIST
    assert window.current_deck_id is None


def test_opening_deck_switches_to_editor(window, library) -> None:
    deck = library.create("Гео")
    window.deck_list.refresh()
    window.open_deck(deck.id)
    assert window.current_page() == PAGE_DECK
    assert window.current_deck_id == deck.id


def test_editor_shows_deck_cards(window, library) -> None:
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")
    window.open_deck(deck.id)
    assert len(window.deck_editor.card_ids()) == 2


def test_back_returns_to_list(window, library) -> None:
    deck = library.create("Гео")
    window.open_deck(deck.id)
    window.deck_editor.back_requested.emit()
    assert window.current_page() == PAGE_DECK_LIST
    assert window.current_deck_id is None


def test_opening_missing_deck_falls_back(window) -> None:
    window.open_deck("нет-такого")
    assert window.current_page() == PAGE_DECK_LIST


def test_deck_list_reflects_cards_added_in_editor(window, library) -> None:
    deck = library.create("Гео")
    window.open_deck(deck.id)
    window.deck_editor.add_card_from_markup("Франция", "Париж")
    window.show_deck_list()
    subtitle = window.deck_list.findChild(object, "deckList").item(0).data(SUBTITLE_ROLE)
    assert "1" in subtitle
