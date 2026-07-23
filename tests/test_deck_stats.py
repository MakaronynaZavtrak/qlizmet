"""Тесты подсчёта статистики по набору."""
from datetime import datetime, timedelta, timezone

import pytest

from qlizmet.core.models import Card, CardFace, CardProgress
from qlizmet.core.stats import MATURE_INTERVAL_DAYS, compute_deck_stats

NOW = datetime(2026, 1, 10, tzinfo=timezone.utc)


def _card(front: str, back: str) -> Card:
    return Card.create(CardFace.from_text(front), CardFace.from_text(back))


CARDS = [_card("Франция", "Париж"), _card("Италия", "Рим"), _card("Испания", "Мадрид")]


def test_empty_deck() -> None:
    stats = compute_deck_stats([], {}, now=NOW)
    assert stats.total == 0
    assert stats.mastery == 0.0
    assert stats.accuracy == 0.0


def test_all_cards_new_by_default() -> None:
    stats = compute_deck_stats(CARDS, {}, now=NOW)
    assert stats.total == 3
    assert stats.new == 3
    assert stats.studied == 0


def test_new_cards_count_as_due() -> None:
    """Новую карточку показываем при первой возможности."""
    stats = compute_deck_stats(CARDS, {}, now=NOW)
    assert stats.due == 3


def test_learning_and_mature_split() -> None:
    progress = {
        CARDS[0].id: CardProgress(CARDS[0].id, interval_days=3),
        CARDS[1].id: CardProgress(CARDS[1].id, interval_days=MATURE_INTERVAL_DAYS),
    }
    stats = compute_deck_stats(CARDS, progress, now=NOW)
    assert stats.learning == 1
    assert stats.mature == 1
    assert stats.new == 1
    assert stats.studied == 2


def test_due_counts_only_ready_cards() -> None:
    progress = {
        CARDS[0].id: CardProgress(CARDS[0].id, interval_days=3, due_at=NOW - timedelta(days=1)),
        CARDS[1].id: CardProgress(CARDS[1].id, interval_days=3, due_at=NOW + timedelta(days=5)),
        CARDS[2].id: CardProgress(CARDS[2].id, interval_days=3, due_at=NOW),
    }
    stats = compute_deck_stats(CARDS, progress, now=NOW)
    assert stats.due == 2  # просроченная и ровно сегодняшняя


def test_mastery_fraction() -> None:
    progress = {
        card.id: CardProgress(card.id, interval_days=MATURE_INTERVAL_DAYS)
        for card in CARDS[:2]
    }
    stats = compute_deck_stats(CARDS, progress, now=NOW)
    assert stats.mastery == pytest.approx(2 / 3)


def test_accuracy_fraction() -> None:
    stats = compute_deck_stats(CARDS, {}, reviews=10, correct=7, now=NOW)
    assert stats.accuracy == pytest.approx(0.7)


def test_accuracy_without_reviews_is_zero() -> None:
    assert compute_deck_stats(CARDS, {}, now=NOW).accuracy == 0.0


def test_progress_of_unknown_cards_is_ignored() -> None:
    """Прогресс по чужой карточке не должен влиять на сводку."""
    stats = compute_deck_stats(
        CARDS, {"чужая-карточка": CardProgress("чужая-карточка", interval_days=30)}, now=NOW
    )
    assert stats.new == 3
    assert stats.mature == 0