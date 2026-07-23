"""Подсчёт статистики по набору.

Чистая логика: функция получает карточки, их прогресс и сводку по ответам, а
возвращает готовые числа. Ни SQL, ни Qt здесь нет, поэтому всё проверяется
обычными тестами.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from qlizmet.core.clock import utcnow
from qlizmet.core.models import Card, CardProgress

#: С какого интервала карточка считается закреплённой (как в Anki — три недели).
MATURE_INTERVAL_DAYS = 21


@dataclass(frozen=True, slots=True)
class DeckStats:
    """Сводка по набору."""

    total: int
    new: int
    learning: int
    mature: int
    due: int
    reviews: int
    correct: int

    @property
    def studied(self) -> int:
        """Сколько карточек хоть раз показывали."""
        return self.learning + self.mature

    @property
    def accuracy(self) -> float:
        """Доля верных ответов за всю историю (0..1)."""
        return self.correct / self.reviews if self.reviews else 0.0

    @property
    def mastery(self) -> float:
        """Доля закреплённых карточек (0..1) — им и меряем прогресс по набору."""
        return self.mature / self.total if self.total else 0.0


def compute_deck_stats(
    cards: Sequence[Card],
    progress: dict[str, CardProgress],
    *,
    reviews: int = 0,
    correct: int = 0,
    now: datetime | None = None,
) -> DeckStats:
    """Собрать сводку по набору.

    ``progress`` — состояния SRS по идентификаторам карточек; карточки без записи
    считаются новыми.
    """
    moment = now or utcnow()
    new = learning = mature = due = 0

    for card in cards:
        state = progress.get(card.id)
        if state is None:
            new += 1
            due += 1  # новую карточку показываем при первой возможности
            continue
        if state.interval_days >= MATURE_INTERVAL_DAYS:
            mature += 1
        else:
            learning += 1
        if state.is_due(now=moment):
            due += 1

    return DeckStats(
        total=len(cards),
        new=new,
        learning=learning,
        mature=mature,
        due=due,
        reviews=reviews,
        correct=correct,
    )