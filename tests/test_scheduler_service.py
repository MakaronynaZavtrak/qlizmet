"""Тесты сервиса расписания и запросов «что пора повторить»."""
from datetime import datetime, timedelta, timezone

import pytest

from qlizmet.app.library_service import LibraryService
from qlizmet.app.scheduler_service import SchedulerService
from qlizmet.app.study_service import StudyService
from qlizmet.core.models import CardProgress
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
    return LibraryService(decks), progress, SchedulerService(decks, progress)


def _deck(library, title="Гео", rows="Франция\tПариж\nИталия\tРим\nИспания\tМадрид"):
    return library.import_tsv(rows, title)


# --- план набора ---


def test_fresh_deck_is_all_new(env) -> None:
    library, _, scheduler = env
    deck = _deck(library)

    plan = scheduler.deck_plan(deck.id, now=NOW)
    assert plan.new_count == 3
    assert plan.due_count == 0
    assert plan.total == 3


def test_answered_card_leaves_the_new_pile(env) -> None:
    library, progress, scheduler = env
    deck = _deck(library)
    StudyService(progress).record(deck.cards[0].id, Grade.GOOD, mode="write", now=NOW)

    plan = scheduler.deck_plan(deck.id, now=NOW)
    assert plan.new_count == 2
    assert deck.cards[0].id not in plan.new_ids


def test_card_is_not_due_until_its_date(env) -> None:
    library, progress, scheduler = env
    deck = _deck(library)
    StudyService(progress).record(deck.cards[0].id, Grade.GOOD, mode="write", now=NOW)

    # интервал после первого верного ответа — один день
    same_day = scheduler.deck_plan(deck.id, now=NOW)
    assert same_day.due_count == 0

    next_day = scheduler.deck_plan(deck.id, now=NOW + timedelta(days=1))
    assert deck.cards[0].id in next_day.due_ids


def test_overdue_cards_come_first(env) -> None:
    """Самые просроченные должны идти в начале очереди."""
    library, progress, scheduler = env
    deck = _deck(library)
    progress.save(CardProgress(deck.cards[0].id, interval_days=5, due_at=NOW - timedelta(days=1)))
    progress.save(CardProgress(deck.cards[1].id, interval_days=5, due_at=NOW - timedelta(days=9)))

    plan = scheduler.deck_plan(deck.id, now=NOW)
    assert plan.due_ids[0] == deck.cards[1].id  # просрочена сильнее


def test_progress_without_date_counts_as_due(env) -> None:
    """Прогресс без даты означает «показать при первой возможности»."""
    library, progress, scheduler = env
    deck = _deck(library)
    progress.save(CardProgress.new(deck.cards[0].id))

    plan = scheduler.deck_plan(deck.id, now=NOW)
    assert deck.cards[0].id in plan.due_ids


def test_plan_ignores_other_decks(env) -> None:
    library, progress, scheduler = env
    mine = _deck(library, "Гео")
    other = _deck(library, "Химия", "Кислород\tO")
    progress.save(CardProgress(other.cards[0].id, due_at=NOW - timedelta(days=1)))

    plan = scheduler.deck_plan(mine.id, now=NOW)
    assert other.cards[0].id not in plan.due_ids


# --- счётчики по всем наборам ---


def test_pending_by_deck(env) -> None:
    library, progress, scheduler = env
    geo = _deck(library, "Гео")
    chem = _deck(library, "Химия", "Кислород\tO\nВодород\tH")
    StudyService(progress).record(geo.cards[0].id, Grade.GOOD, mode="write", now=NOW)

    counts = scheduler.pending_by_deck(now=NOW)
    assert counts[geo.id].new == 2
    assert counts[chem.id].new == 2


def test_empty_deck_has_no_pending(env) -> None:
    library, _, scheduler = env
    deck = library.create("Пустой")
    assert deck.id not in scheduler.pending_by_deck(now=NOW)


def test_total_pending_sums_decks(env) -> None:
    library, _, scheduler = env
    _deck(library, "Гео")
    _deck(library, "Химия", "Кислород\tO")

    total = scheduler.total_pending(now=NOW)
    assert total.new == 4
    assert total.total == 4


# --- очередь карточек ---


def test_session_cards_follow_plan_order(env) -> None:
    library, progress, scheduler = env
    deck = _deck(library)
    progress.save(CardProgress(deck.cards[2].id, interval_days=5, due_at=NOW - timedelta(days=2)))

    cards = scheduler.cards_for_session(deck.id, now=NOW)
    assert cards[0].id == deck.cards[2].id  # повтор впереди новых
    assert len(cards) == 3


def test_session_respects_new_limit(env) -> None:
    library, _, scheduler = env
    deck = _deck(library)
    assert len(scheduler.cards_for_session(deck.id, new_limit=1, now=NOW)) == 1


def test_session_of_studied_deck_can_be_empty(env) -> None:
    """Всё повторено и ничего нового — заниматься сегодня нечем."""
    library, progress, scheduler = env
    deck = _deck(library, "Гео", "Франция\tПариж")
    StudyService(progress).record(deck.cards[0].id, Grade.GOOD, mode="write", now=NOW)

    assert scheduler.cards_for_session(deck.id, now=NOW) == []


def test_session_for_missing_deck_raises(env) -> None:
    _, _, scheduler = env
    with pytest.raises(LookupError):
        scheduler.cards_for_session("нет-такого")
