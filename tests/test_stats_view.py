"""Тесты экрана статистики и перехода к нему."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from qlizmet.app.deck_service import DeckService  # noqa: E402
from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.app.stats_service import StatsService  # noqa: E402
from qlizmet.app.study_service import StudyService  # noqa: E402
from qlizmet.core.models import CardProgress  # noqa: E402
from qlizmet.core.srs import Grade  # noqa: E402
from qlizmet.storage.sqlite.repositories import (  # noqa: E402
    SqliteDeckRepository,
    SqliteProgressRepository,
)
from qlizmet.ui.main_window import PAGE_DECK, PAGE_STATS, MainWindow  # noqa: E402
from qlizmet.ui.views.stats_view import StatsView  # noqa: E402


@pytest.fixture
def env(conn):
    decks = SqliteDeckRepository(conn)
    progress = SqliteProgressRepository(conn)
    return (
        LibraryService(decks),
        progress,
        StatsService(decks, progress),
        DeckService(decks),
    )


def _value(view: StatsView, name: str) -> str:
    return view.findChild(object, name).text()


def test_fresh_deck_shows_all_new(env, qt_host) -> None:
    library, _, stats, _ = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")

    view = StatsView(stats, parent=qt_host)
    view.load(deck.id)

    assert _value(view, "totalValue") == "2"
    assert _value(view, "newValue") == "2"
    assert _value(view, "dueValue") == "2"


def test_no_reviews_message(env, qt_host) -> None:
    library, _, stats, _ = env
    deck = library.import_tsv("Франция\tПариж", "Гео")

    view = StatsView(stats, parent=qt_host)
    view.load(deck.id)

    assert "пока нет ответов" in _value(view, "accuracyValue")
    assert "не изучался" in view.hint_text()


def test_empty_deck_hint(env, qt_host) -> None:
    library, _, stats, _ = env
    deck = library.create("Пустой")

    view = StatsView(stats, parent=qt_host)
    view.load(deck.id)

    assert _value(view, "totalValue") == "0"
    assert "нет карточек" in view.hint_text()


def test_accuracy_after_answers(env, qt_host) -> None:
    library, progress, stats, _ = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")
    service = StudyService(progress)
    service.record(deck.cards[0].id, Grade.GOOD, mode="write")
    service.record(deck.cards[1].id, Grade.AGAIN, mode="write")

    view = StatsView(stats, parent=qt_host)
    view.load(deck.id)

    assert "50%" in _value(view, "accuracyValue")
    assert _value(view, "learningValue") == "2"


def test_mastery_bar_reflects_mature_share(env, qt_host) -> None:
    library, progress, stats, _ = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")
    progress.save(CardProgress(deck.cards[0].id, interval_days=30))

    view = StatsView(stats, parent=qt_host)
    view.load(deck.id)

    assert _value(view, "matureValue") == "1"
    assert view.findChild(object, "masteryBar").value() == 50


def test_refresh_picks_up_new_answers(env, qt_host) -> None:
    library, progress, stats, _ = env
    deck = library.import_tsv("Франция\tПариж", "Гео")

    view = StatsView(stats, parent=qt_host)
    view.load(deck.id)
    assert "пока нет ответов" in _value(view, "accuracyValue")

    StudyService(progress).record(deck.cards[0].id, Grade.GOOD, mode="write")
    view.refresh()
    assert "100%" in _value(view, "accuracyValue")


def test_view_without_service_degrades(qt_host) -> None:
    view = StatsView(parent=qt_host)
    view.load("любой-набор")  # не должно падать
    assert "недоступна" in view.hint_text()


def test_navigation_to_stats_and_back(env, qt_host) -> None:
    library, _, stats, decks = env
    deck = library.import_tsv("Франция\tПариж", "Гео")

    window = MainWindow(library, decks, stats=stats, parent=qt_host)
    window.open_deck(deck.id)
    window.deck_editor.stats_requested.emit()

    assert window.current_page() == PAGE_STATS
    assert window.stats_view.deck_id == deck.id

    window.stats_view.back_requested.emit()
    assert window.current_page() == PAGE_DECK


def test_stats_button_exists_in_editor(env, qt_host) -> None:
    library, _, stats, decks = env
    deck = library.create("Гео")
    window = MainWindow(library, decks, stats=stats, parent=qt_host)
    window.open_deck(deck.id)

    assert window.deck_editor.findChild(object, "statsButton") is not None