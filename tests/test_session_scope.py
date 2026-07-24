"""Тесты области занятия: весь набор или только на сегодня."""
from datetime import datetime, timedelta, timezone

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
from qlizmet.core.study import SessionScope, StudyMode  # noqa: E402
from qlizmet.storage.sqlite.repositories import (  # noqa: E402
    SqliteDeckRepository,
    SqliteProgressRepository,
)
from qlizmet.ui.main_window import PAGE_WRITE, MainWindow  # noqa: E402
from qlizmet.ui.views.mode_select_view import (  # noqa: E402
    NOTHING_TODAY_HINT,
    ModeSelectView,
)

NOW = datetime(2026, 1, 10, tzinfo=timezone.utc)


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


@pytest.fixture
def view(env, qt_host) -> ModeSelectView:
    library, decks, _, scheduler = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим\nИспания\tМадрид", "Гео")
    screen = ModeSelectView(decks, scheduler=scheduler, parent=qt_host)
    screen.load(deck.id)
    screen.deck = deck  # для удобства тестов
    return screen


def test_default_scope_is_whole_deck(view) -> None:
    assert view.scope is SessionScope.ALL
    assert len(view.scoped_cards()) == 3


def test_scope_buttons_show_counts(view) -> None:
    assert "(3)" in view.findChild(object, "scope_all").text()
    assert "(3)" in view.findChild(object, "scope_due_today").text()


def test_fresh_deck_has_everything_due_today(view) -> None:
    view.set_scope(SessionScope.DUE_TODAY)
    assert len(view.scoped_cards()) == 3  # все карточки новые


def test_studied_deck_has_nothing_today(env, qt_host) -> None:
    library, decks, progress, scheduler = env
    deck = library.import_tsv("Франция\tПариж", "Гео")
    StudyService(progress).record(deck.cards[0].id, Grade.GOOD, mode="write")

    view = ModeSelectView(decks, scheduler=scheduler, parent=qt_host)
    view.load(deck.id)
    view.set_scope(SessionScope.DUE_TODAY)

    assert view.scoped_cards() == []
    assert view.enabled_modes() == set()


def test_nothing_today_explains_itself(env, qt_host) -> None:
    """Причина должна быть понятной, а не «нужна хотя бы одна карточка»."""
    library, decks, progress, scheduler = env
    deck = library.import_tsv("Франция\tПариж", "Гео")
    StudyService(progress).record(deck.cards[0].id, Grade.GOOD, mode="write")

    view = ModeSelectView(decks, scheduler=scheduler, parent=qt_host)
    view.load(deck.id)
    view.set_scope(SessionScope.DUE_TODAY)

    assert view.button_for(StudyMode.FLASHCARDS).hint_text() == NOTHING_TODAY_HINT


def test_scope_changes_mode_availability(env, qt_host) -> None:
    """На сегодня одна карточка — игре на пары нечего сопоставлять."""
    library, decks, progress, scheduler = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим\nИспания\tМадрид", "Гео")
    # две карточки уже изучены и не просрочены, одна осталась новой
    for card in deck.cards[:2]:
        # экран спрашивает планировщик о текущем моменте, поэтому и дата — от него
        progress.save(
            CardProgress(card.id, interval_days=10, due_at=utcnow() + timedelta(days=5))
        )

    view = ModeSelectView(decks, scheduler=scheduler, parent=qt_host)
    view.load(deck.id)

    assert StudyMode.MATCH in view.enabled_modes()  # весь набор — три карточки
    view.set_scope(SessionScope.DUE_TODAY)
    assert len(view.scoped_cards()) == 1
    assert StudyMode.MATCH not in view.enabled_modes()
    assert StudyMode.FLASHCARDS in view.enabled_modes()


def test_switching_scope_back_restores_modes(view) -> None:
    view.set_scope(SessionScope.DUE_TODAY)
    view.set_scope(SessionScope.ALL)
    assert StudyMode.MATCH in view.enabled_modes()


def test_scope_buttons_are_exclusive(view) -> None:
    view.set_scope(SessionScope.DUE_TODAY)
    assert view.findChild(object, "scope_due_today").isChecked()
    assert not view.findChild(object, "scope_all").isChecked()


def test_today_scope_disabled_without_scheduler(env, qt_host) -> None:
    """Без планировщика выбирать «на сегодня» не из чего."""
    library, decks, _, _ = env
    deck = library.import_tsv("Франция\tПариж", "Гео")
    view = ModeSelectView(decks, parent=qt_host)
    view.load(deck.id)

    assert not view.findChild(object, "scope_due_today").isEnabled()


# --- запуск режима с выбранной очередью ---


def test_mode_starts_with_scoped_cards(env, qt_host) -> None:
    library, decks, progress, scheduler = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим\nИспания\tМадрид", "Гео")
    for card in deck.cards[:2]:
        # экран спрашивает планировщик о текущем моменте, поэтому и дата — от него
        progress.save(
            CardProgress(card.id, interval_days=10, due_at=utcnow() + timedelta(days=5))
        )

    window = MainWindow(
        library, decks, scheduler=scheduler, parent=qt_host
    )
    window.open_deck(deck.id)
    window.show_modes()
    window.modes.set_scope(SessionScope.DUE_TODAY)
    window.start_mode("write")

    assert window.current_page() == PAGE_WRITE
    assert window.write.progress_text() == "1 / 1"  # только несделанная карточка


def test_mode_starts_with_whole_deck_by_default(env, qt_host) -> None:
    library, decks, _, scheduler = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")

    window = MainWindow(library, decks, scheduler=scheduler, parent=qt_host)
    window.open_deck(deck.id)
    window.show_modes()
    window.start_mode("write")

    assert window.write.progress_text() == "1 / 2"
