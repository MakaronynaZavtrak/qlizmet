"""Тесты сервиса статистики и пакетных запросов прогресса."""
from datetime import datetime, timedelta, timezone

import pytest

from qlizmet.app.library_service import LibraryService
from qlizmet.app.stats_service import StatsService
from qlizmet.app.study_service import StudyService
from qlizmet.core.models import CardProgress, ReviewRecord
from qlizmet.core.srs import Grade
from qlizmet.storage.sqlite.repositories import (
    SqliteDeckRepository,
    SqliteProgressRepository,
)

NOW = datetime(2026, 1, 10, tzinfo=timezone.utc)


@pytest.fixture
def env(conn):
    decks = SqliteDeckRepository(conn)
    progress = SqliteProgressRepository(conn)
    library = LibraryService(decks)
    return library, progress, StatsService(decks, progress)


def test_stats_of_fresh_deck(env) -> None:
    library, _, stats = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")

    summary = stats.deck_stats(deck.id, now=NOW)
    assert summary.total == 2
    assert summary.new == 2
    assert summary.reviews == 0


def test_stats_missing_deck_raises(env) -> None:
    _, _, stats = env
    with pytest.raises(LookupError):
        stats.deck_stats("нет-такого")


def test_stats_reflect_answers(env) -> None:
    library, progress, stats = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")
    service = StudyService(progress)

    service.record(deck.cards[0].id, Grade.GOOD, mode="write", now=NOW)
    service.record(deck.cards[1].id, Grade.AGAIN, mode="write", now=NOW)

    summary = stats.deck_stats(deck.id, now=NOW)
    assert summary.reviews == 2
    assert summary.correct == 1
    assert summary.accuracy == pytest.approx(0.5)
    assert summary.new == 0
    assert summary.learning == 2


def test_stats_counts_mature_cards(env) -> None:
    library, progress, stats = env
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")
    progress.save(CardProgress(deck.cards[0].id, interval_days=30))

    summary = stats.deck_stats(deck.id, now=NOW)
    assert summary.mature == 1
    assert summary.mastery == pytest.approx(0.5)


def test_stats_ignore_other_decks(env) -> None:
    """Ответы по чужому набору не должны попадать в сводку этого."""
    library, progress, stats = env
    mine = library.import_tsv("Франция\tПариж", "Гео")
    other = library.import_tsv("Кислород\tO", "Химия")

    StudyService(progress).record(other.cards[0].id, Grade.GOOD, mode="write", now=NOW)

    summary = stats.deck_stats(mine.id, now=NOW)
    assert summary.reviews == 0


# --- пакетные запросы репозитория ---


def test_progress_for_empty_list(conn) -> None:
    assert SqliteProgressRepository(conn).progress_for([]) == {}


def test_progress_for_returns_only_requested(conn) -> None:
    library = LibraryService(SqliteDeckRepository(conn))
    progress = SqliteProgressRepository(conn)
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")
    progress.save(CardProgress(deck.cards[0].id, interval_days=4))

    states = progress.progress_for([card.id for card in deck.cards])
    assert list(states) == [deck.cards[0].id]
    assert states[deck.cards[0].id].interval_days == 4


def test_review_totals_empty(conn) -> None:
    assert SqliteProgressRepository(conn).review_totals([]) == (0, 0)


def test_review_totals_counts_correct(conn) -> None:
    library = LibraryService(SqliteDeckRepository(conn))
    progress = SqliteProgressRepository(conn)
    deck = library.import_tsv("Франция\tПариж", "Гео")
    card = deck.cards[0]

    progress.add_review(ReviewRecord(card.id, NOW, mode="write", is_correct=True))
    progress.add_review(
        ReviewRecord(card.id, NOW + timedelta(days=1), mode="write", is_correct=False)
    )

    assert progress.review_totals([card.id]) == (2, 1)