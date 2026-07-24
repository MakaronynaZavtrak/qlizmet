"""Тесты быстрого перехода к повторению и счётчиков «на сегодня»."""
from datetime import timedelta

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from qlizmet.app.deck_service import DeckService  # noqa: E402
from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.app.scheduler_service import SchedulerService  # noqa: E402
from qlizmet.app.study_service import StudyService  # noqa: E402
from qlizmet.core.clock import utcnow  # noqa: E402
from qlizmet.core.models import CardProgress  # noqa: E402
from qlizmet.core.srs import Grade  # noqa: E402
from qlizmet.core.study import SessionScope  # noqa: E402
from qlizmet.storage.sqlite.repositories import (  # noqa: E402
    SqliteDeckRepository,
    SqliteProgressRepository,
)
from qlizmet.ui.main_window import PAGE_MODES, MainWindow  # noqa: E402
from qlizmet.ui.views.deck_list_view import DeckListView  # noqa: E402
from qlizmet.ui.widgets.list_delegate import BADGE_ROLE  # noqa: E402


@pytest.fixture
def env(conn):
    decks = SqliteDeckRepository(conn)
    progress = SqliteProgressRepository(conn)
    return (
        LibraryService(decks),
        DeckService(decks),
        progress,
        SchedulerService(decks, progress),
    )


def _later(days: int):
    """Дата в будущем относительно настоящего момента — карточка ещё не просрочена."""
    return utcnow() + timedelta(days=days)


# --- счётчик в списке наборов ---


def test_badge_shows_pending_count(env, qt_host) -> None:
    library, _, _, scheduler = env
    library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")

    view = DeckListView(library, scheduler=scheduler, parent=qt_host)
    badge = view.findChild(object, "deckList").item(0).data(BADGE_ROLE)
    assert "2" in badge


def test_no_badge_when_nothing_pending(env, qt_host) -> None:
    library, _, progress, scheduler = env
    deck = library.import_tsv("Франция\tПариж", "Гео")
    StudyService(progress).record(deck.cards[0].id, Grade.GOOD, mode="write")

    view = DeckListView(library, scheduler=scheduler, parent=qt_host)
    assert view.findChild(object, "deckList").item(0).data(BADGE_ROLE) is None


def test_no_badge_without_scheduler(env, qt_host) -> None:
    library, _, _, _ = env
    library.import_tsv("Франция\tПариж", "Гео")

    view = DeckListView(library, parent=qt_host)
    assert view.findChild(object, "deckList").item(0).data(BADGE_ROLE) is None


def test_badge_updates_after_studying(env, qt_host) -> None:
    library, _, progress, scheduler = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")

    view = DeckListView(library, scheduler=scheduler, parent=qt_host)
    StudyService(progress).record(deck.cards[0].id, Grade.GOOD, mode="write")
    view.refresh()

    assert "1" in view.findChild(object, "deckList").item(0).data(BADGE_ROLE)


# --- кнопка в редакторе ---


def test_review_button_shows_count(env, qt_host) -> None:
    library, decks, _, scheduler = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")

    window = MainWindow(library, decks, scheduler=scheduler, parent=qt_host)
    window.open_deck(deck.id)

    button = window.deck_editor.findChild(object, "reviewButton")
    assert "2" in button.text()
    assert button.isEnabled()


def test_review_button_disabled_when_nothing_due(env, qt_host) -> None:
    library, decks, progress, scheduler = env
    deck = library.import_tsv("Франция\tПариж", "Гео")
    StudyService(progress).record(deck.cards[0].id, Grade.GOOD, mode="write")

    window = MainWindow(library, decks, scheduler=scheduler, parent=qt_host)
    window.open_deck(deck.id)

    button = window.deck_editor.findChild(object, "reviewButton")
    assert not button.isEnabled()
    assert "всё повторено" in button.toolTip()


def test_review_button_opens_today_scope(env, qt_host) -> None:
    library, decks, progress, scheduler = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим\nИспания\tМадрид", "Гео")
    progress.save(CardProgress(deck.cards[0].id, interval_days=10, due_at=_later(5)))

    window = MainWindow(library, decks, scheduler=scheduler, parent=qt_host)
    window.open_deck(deck.id)
    window.deck_editor.review_requested.emit()

    assert window.current_page() == PAGE_MODES
    assert window.modes.scope is SessionScope.DUE_TODAY
    assert len(window.modes.scoped_cards()) == 2  # третья ещё не просрочена


def test_regular_study_button_keeps_whole_deck(env, qt_host) -> None:
    library, decks, progress, scheduler = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")
    progress.save(CardProgress(deck.cards[0].id, interval_days=10, due_at=_later(5)))

    window = MainWindow(library, decks, scheduler=scheduler, parent=qt_host)
    window.open_deck(deck.id)
    window.show_modes()

    assert window.modes.scope is SessionScope.ALL
    assert len(window.modes.scoped_cards()) == 2


def test_pending_count_refreshes_after_session(env, qt_host) -> None:
    """Позанимались — счётчик на кнопке должен уменьшиться."""
    library, decks, progress, scheduler = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")

    window = MainWindow(library, decks, scheduler=scheduler, parent=qt_host)
    window.open_deck(deck.id)
    assert "2" in window.deck_editor.findChild(object, "reviewButton").text()

    StudyService(progress).record(deck.cards[0].id, Grade.GOOD, mode="write")
    window.show_modes()
    window.modes.back_requested.emit()  # возврат в редактор

    assert "1" in window.deck_editor.findChild(object, "reviewButton").text()


def test_editor_without_scheduler_hides_count(env, qt_host) -> None:
    library, decks, _, _ = env
    deck = library.import_tsv("Франция\tПариж", "Гео")

    window = MainWindow(library, decks, parent=qt_host)
    window.open_deck(deck.id)

    button = window.deck_editor.findChild(object, "reviewButton")
    assert not button.isEnabled()
