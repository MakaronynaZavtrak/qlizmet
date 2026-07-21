"""Тесты прикладного сервиса записи прогресса (SM-2 × хранилище)."""
from datetime import datetime, timezone

from qlizmet.app import StudyService, grade_from_verdict
from qlizmet.core.grading import Verdict
from qlizmet.core.models import Card, CardFace, CardProgress, Deck
from qlizmet.core.srs import Grade
from qlizmet.storage.sqlite.repositories import (
    SqliteDeckRepository,
    SqliteProgressRepository,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _saved_card(conn) -> Card:
    """Создать набор с карточкой в БД (нужно для внешнего ключа прогресса)."""
    deck = Deck.create("Гео", now=NOW)
    card = Card.create(CardFace.from_text("Франция"), CardFace.from_text("Париж"), now=NOW)
    deck.add_card(card, now=NOW)
    SqliteDeckRepository(conn).save(deck)
    return card


def test_first_correct_creates_progress_and_review(conn) -> None:
    card = _saved_card(conn)
    progress_repo = SqliteProgressRepository(conn)
    service = StudyService(progress_repo)

    service.record(card.id, Grade.GOOD, mode="learn", now=NOW)

    saved = progress_repo.get(card.id)
    assert saved.interval_days == 1
    assert saved.repetitions == 1

    history = progress_repo.reviews_for(card.id)
    assert len(history) == 1
    assert history[0].is_correct
    assert history[0].quality == 4
    assert history[0].mode == "learn"


def test_repeated_reviews_advance_interval(conn) -> None:
    card = _saved_card(conn)
    progress_repo = SqliteProgressRepository(conn)
    service = StudyService(progress_repo)

    service.record(card.id, Grade.GOOD, mode="learn", now=NOW)
    service.record(card.id, Grade.GOOD, mode="learn", now=NOW)

    assert progress_repo.get(card.id).interval_days == 6
    assert len(progress_repo.reviews_for(card.id)) == 2


def test_failure_records_incorrect_and_lapse(conn) -> None:
    card = _saved_card(conn)
    progress_repo = SqliteProgressRepository(conn)
    service = StudyService(progress_repo)

    service.record(card.id, Grade.GOOD, mode="learn", now=NOW)  # довели до повтора
    service.record(card.id, Grade.AGAIN, mode="learn", now=NOW)  # сорвались

    saved = progress_repo.get(card.id)
    assert saved.interval_days == 1
    assert saved.lapses == 1
    assert progress_repo.reviews_for(card.id)[-1].is_correct is False


def test_uses_existing_progress(conn) -> None:
    card = _saved_card(conn)
    progress_repo = SqliteProgressRepository(conn)
    progress_repo.save(CardProgress(card.id, ease=2.5, interval_days=6, repetitions=2))
    service = StudyService(progress_repo)

    updated = service.record(card.id, Grade.GOOD, mode="learn", now=NOW)

    assert updated.interval_days == 15  # round(6 * 2.5), а не начало с нуля
    assert updated.repetitions == 3


def test_write_verdict_flow_persists(conn) -> None:
    card = _saved_card(conn)
    progress_repo = SqliteProgressRepository(conn)
    service = StudyService(progress_repo)

    grade = grade_from_verdict(Verdict.INCORRECT)
    service.record(card.id, grade, mode="write", now=NOW, user_answer="Лондон")

    review = progress_repo.reviews_for(card.id)[0]
    assert review.mode == "write"
    assert review.is_correct is False
    assert review.user_answer == "Лондон"


def test_grade_from_verdict_mapping() -> None:
    assert grade_from_verdict(Verdict.EXACT) is Grade.GOOD
    assert grade_from_verdict(Verdict.TYPO) is Grade.HARD
    assert grade_from_verdict(Verdict.INCORRECT) is Grade.AGAIN


def test_metadata_is_persisted(conn) -> None:
    card = _saved_card(conn)
    progress_repo = SqliteProgressRepository(conn)
    service = StudyService(progress_repo)

    service.record(
        card.id, Grade.GOOD, mode="write", now=NOW, user_answer="париж", response_ms=1500
    )
    review = progress_repo.reviews_for(card.id)[0]
    assert review.user_answer == "париж"
    assert review.response_ms == 1500