"""Тесты репозитория прогресса и истории ответов."""
from datetime import datetime, timedelta, timezone

from qlizmet.core.models import (
    Card,
    CardFace,
    CardProgress,
    Deck,
    ReviewRecord,
)
from qlizmet.storage.sqlite.repositories import (
    SqliteDeckRepository,
    SqliteProgressRepository,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _deck_with_one_card(conn) -> Card:
    """Сохранить набор с одной карточкой и вернуть эту карточку.

    Карточка должна существовать в БД, иначе внешний ключ не даст записать
    прогресс или ответ по ней.
    """
    deck = Deck.create("Гео", now=NOW)
    card = Card.create(CardFace.from_text("Франция"), CardFace.from_text("Париж"), now=NOW)
    deck.add_card(card, now=NOW)
    SqliteDeckRepository(conn).save(deck)
    return card


def test_progress_save_and_get(conn) -> None:
    card = _deck_with_one_card(conn)
    repo = SqliteProgressRepository(conn)
    repo.save(CardProgress(card.id, ease=2.6, interval_days=10, repetitions=3, lapses=1))

    loaded = repo.get(card.id)
    assert loaded is not None
    assert loaded.ease == 2.6
    assert loaded.interval_days == 10
    assert loaded.lapses == 1


def test_progress_get_missing(conn) -> None:
    assert SqliteProgressRepository(conn).get("нет-такого") is None


def test_reviews_are_returned_in_order(conn) -> None:
    card = _deck_with_one_card(conn)
    repo = SqliteProgressRepository(conn)
    repo.add_review(
        ReviewRecord(card.id, NOW, mode="write", is_correct=True, quality=5)
    )
    repo.add_review(
        ReviewRecord(card.id, NOW + timedelta(days=1), mode="write", is_correct=False, quality=1)
    )

    history = repo.reviews_for(card.id)
    assert len(history) == 2
    assert history[0].quality == 5
    assert history[1].quality == 1


def test_delete_deck_cascades_progress_and_reviews(conn) -> None:
    card = _deck_with_one_card(conn)
    decks = SqliteDeckRepository(conn)
    progress = SqliteProgressRepository(conn)
    progress.save(CardProgress(card.id, interval_days=4))
    progress.add_review(ReviewRecord(card.id, NOW, mode="test", is_correct=True))

    deck_id = decks.list_deck_ids()[0]
    decks.delete(deck_id)

    assert progress.get(card.id) is None
    assert progress.reviews_for(card.id) == []