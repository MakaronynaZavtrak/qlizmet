"""Тесты экрана со списком наборов и навигации главного окна."""
import pytest

pytest.importorskip("PySide6")

from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.storage.sqlite.repositories import SqliteDeckRepository  # noqa: E402
from qlizmet.ui.main_window import PAGE_DECK, PAGE_DECK_LIST, MainWindow  # noqa: E402
from qlizmet.ui.views.deck_list_view import DeckListView  # noqa: E402


@pytest.fixture
def library(conn) -> LibraryService:
    return LibraryService(SqliteDeckRepository(conn))


@pytest.fixture
def view(library, qt_host) -> DeckListView:
    return DeckListView(library, parent=qt_host)


def test_empty_state_hint_visible(view) -> None:
    assert view.deck_ids() == []
    assert view.findChild(object, "emptyHint") is not None


def test_created_deck_appears(view) -> None:
    deck_id = view.create_deck("Гео", "столицы")
    assert view.deck_ids() == [deck_id]
    assert view.selected_deck_id() == deck_id


def test_list_shows_title_and_count(view) -> None:
    view.import_deck("Франция\tПариж\nИталия\tРим", "Гео")
    text = view.findChild(object, "deckList").item(0).text()
    assert "Гео" in text
    assert "2" in text


def test_refresh_picks_up_external_changes(view, library) -> None:
    library.create("Извне")
    view.refresh()
    assert len(view.deck_ids()) == 1


def test_delete_removes_from_list(view) -> None:
    deck_id = view.create_deck("Гео")
    assert view.delete_deck(deck_id) is True
    assert view.deck_ids() == []


def test_selection_survives_refresh(view) -> None:
    view.create_deck("Первый")
    second = view.create_deck("Второй")
    view.select_deck(second)
    view.refresh()
    assert view.selected_deck_id() == second


def test_open_selected_emits_signal(view) -> None:
    deck_id = view.create_deck("Гео")
    opened: list[str] = []
    view.deck_opened.connect(opened.append)
    view.open_selected()
    assert opened == [deck_id]


def test_open_without_selection_is_silent(view) -> None:
    opened: list[str] = []
    view.deck_opened.connect(opened.append)
    view.open_selected()
    assert opened == []


def test_window_starts_on_deck_list(library, qt_host) -> None:
    window = MainWindow(library, parent=qt_host)
    assert window.current_page() == PAGE_DECK_LIST
    assert window.current_deck_id is None


def test_opening_deck_switches_page(library, qt_host) -> None:
    deck = library.create("Гео")
    window = MainWindow(library, parent=qt_host)
    window.deck_list.refresh()
    window.open_deck(deck.id)
    assert window.current_page() == PAGE_DECK
    assert window.current_deck_id == deck.id


def test_deck_page_shows_title(library, qt_host) -> None:
    deck = library.import_tsv("Франция\tПариж", "Гео")
    window = MainWindow(library, parent=qt_host)
    window.open_deck(deck.id)
    assert window.findChild(object, "deckTitle").text() == "Гео"
    assert "1" in window.findChild(object, "deckSubtitle").text()


def test_back_to_list(library, qt_host) -> None:
    deck = library.create("Гео")
    window = MainWindow(library, parent=qt_host)
    window.open_deck(deck.id)
    window.show_deck_list()
    assert window.current_page() == PAGE_DECK_LIST
    assert window.current_deck_id is None


def test_opening_missing_deck_falls_back(library, qt_host) -> None:
    window = MainWindow(library, parent=qt_host)
    window.open_deck("нет-такого")
    assert window.current_page() == PAGE_DECK_LIST


def test_double_click_opens_deck(view) -> None:
    deck_id = view.create_deck("Гео")
    opened: list[str] = []
    view.deck_opened.connect(opened.append)
    deck_list = view.findChild(object, "deckList")
    deck_list.itemDoubleClicked.emit(deck_list.item(0))
    assert opened == [deck_id]