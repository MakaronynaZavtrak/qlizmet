"""Тесты экрана со списком наборов и навигации главного окна."""
import pytest

pytest.importorskip("PySide6")

from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.storage.sqlite.repositories import SqliteDeckRepository  # noqa: E402
from qlizmet.ui.views.deck_list_view import DeckListView  # noqa: E402
from qlizmet.ui.widgets.list_delegate import SUBTITLE_ROLE  # noqa: E402


def _row(view, index: int = 0) -> tuple[str, str]:
    """Заголовок и подзаголовок строки списка."""
    item = view.findChild(object, "deckList").item(index)
    return item.text(), item.data(SUBTITLE_ROLE)


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
    title, subtitle = _row(view)
    assert title == "Гео"
    assert "2" in subtitle


def test_list_subtitle_includes_description(view) -> None:
    view.create_deck("Гео", "столицы Европы")
    _, subtitle = _row(view)
    assert "столицы Европы" in subtitle


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


def test_double_click_opens_deck(view) -> None:
    deck_id = view.create_deck("Гео")
    opened: list[str] = []
    view.deck_opened.connect(opened.append)
    deck_list = view.findChild(object, "deckList")
    deck_list.itemDoubleClicked.emit(deck_list.item(0))
    assert opened == [deck_id]
