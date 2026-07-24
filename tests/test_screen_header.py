"""Тесты общей шапки экранов и полоски прогресса в списке."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from PySide6.QtWidgets import QLabel, QPushButton  # noqa: E402

from qlizmet.app.deck_service import DeckService  # noqa: E402
from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.core.models import CardProgress  # noqa: E402
from qlizmet.storage.sqlite.repositories import (  # noqa: E402
    SqliteDeckRepository,
    SqliteProgressRepository,
)
from qlizmet.ui.views.deck_editor_view import DeckEditorView  # noqa: E402
from qlizmet.ui.views.deck_list_view import DeckListView  # noqa: E402
from qlizmet.ui.views.stats_view import StatsView  # noqa: E402
from qlizmet.ui.views.write_view import WriteView  # noqa: E402
from qlizmet.ui.widgets.list_delegate import PROGRESS_ROLE  # noqa: E402
from qlizmet.ui.widgets.screen_header import ScreenHeader  # noqa: E402


# --- шапка ---


def test_header_has_back_button_by_default(qt_host) -> None:
    header = ScreenHeader("Заголовок", parent=qt_host)
    assert header.back_button is not None
    assert header.back_button.objectName() == "backButton"


def test_header_without_back_button(qt_host) -> None:
    """На первом экране возвращаться некуда."""
    header = ScreenHeader("Мои наборы", back_text=None, parent=qt_host)
    assert header.back_button is None


def test_back_button_emits_signal(qt_host) -> None:
    header = ScreenHeader(back_text="Выйти", parent=qt_host)
    seen: list[bool] = []
    header.back_requested.connect(lambda: seen.append(True))
    header.back_button.click()
    assert seen == [True]


def test_header_title(qt_host) -> None:
    header = ScreenHeader("Старый", parent=qt_host)
    header.set_title("Новый")
    assert header.title_text() == "Новый"


def test_header_title_name_is_configurable(qt_host) -> None:
    """Заголовок набора и заголовок экрана оформляются по-разному."""
    deck = ScreenHeader(title_name="deckTitle", parent=qt_host)
    screen = ScreenHeader(title_name="screenTitle", parent=qt_host)
    assert deck.findChild(QLabel, "deckTitle") is not None
    assert screen.findChild(QLabel, "screenTitle") is not None


def test_header_actions_are_added(qt_host) -> None:
    header = ScreenHeader(parent=qt_host)
    button = QPushButton("Действие")
    assert header.add_action(button) is button
    assert button.parent() is header


# --- шапка на реальных экранах ---


@pytest.fixture
def services(conn):
    repo = SqliteDeckRepository(conn)
    return LibraryService(repo), DeckService(repo), SqliteProgressRepository(conn)


def test_editor_uses_shared_header(services, qt_host) -> None:
    library, decks, _ = services
    deck = library.create("Гео")
    view = DeckEditorView(decks, parent=qt_host)
    view.load(deck.id)

    assert view.findChild(ScreenHeader) is not None
    assert view.findChild(QLabel, "deckTitle").text() == "Гео"
    assert view.findChild(QPushButton, "backButton") is not None


def test_stats_uses_shared_header(qt_host) -> None:
    view = StatsView(parent=qt_host)
    assert view.findChild(ScreenHeader) is not None


def test_study_screen_uses_shared_header(qt_host) -> None:
    view = WriteView(parent=qt_host)
    header = view.findChild(ScreenHeader)
    assert header is not None
    assert header.back_button.text() == "Выйти"


def test_deck_list_header_has_no_back_button(services, qt_host) -> None:
    library, _, _ = services
    view = DeckListView(library, parent=qt_host)
    assert view.findChild(ScreenHeader).back_button is None


# --- прогресс в списке наборов ---


def test_empty_deck_has_no_progress(services, qt_host) -> None:
    library, _, _ = services
    view = DeckListView(library, parent=qt_host)
    view.create_deck("Пустой")
    item = view.findChild(object, "deckList").item(0)
    assert item.data(PROGRESS_ROLE) is None


def test_untouched_deck_shows_zero_progress(services, qt_host) -> None:
    library, _, _ = services
    view = DeckListView(library, parent=qt_host)
    view.import_deck("Франция\tПариж\nИталия\tРим", "Гео")
    item = view.findChild(object, "deckList").item(0)
    assert item.data(PROGRESS_ROLE) == 0.0


def test_progress_reflects_mature_cards(services, qt_host) -> None:
    library, _, progress = services
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")
    progress.save(CardProgress(deck.cards[0].id, interval_days=30))

    view = DeckListView(library, parent=qt_host)
    item = view.findChild(object, "deckList").item(0)
    assert item.data(PROGRESS_ROLE) == pytest.approx(0.5)


def test_subtitle_mentions_progress(services, qt_host) -> None:
    library, _, progress = services
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")
    progress.save(CardProgress(deck.cards[0].id, interval_days=30))

    view = DeckListView(library, parent=qt_host)
    from qlizmet.ui.widgets.list_delegate import SUBTITLE_ROLE

    subtitle = view.findChild(object, "deckList").item(0).data(SUBTITLE_ROLE)
    assert "50%" in subtitle


def test_summary_counts_mature_per_deck(services) -> None:
    """Прогресс считается по своему набору, а не по всей базе."""
    library, _, progress = services
    mine = library.import_tsv("Франция\tПариж", "Гео")
    other = library.import_tsv("Кислород\tO", "Химия")
    progress.save(CardProgress(other.cards[0].id, interval_days=30))

    summaries = {s.title: s for s in library.summaries()}
    assert summaries["Гео"].mastery == 0.0
    assert summaries["Химия"].mastery == 1.0
