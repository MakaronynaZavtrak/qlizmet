"""Состояние прогресса по карточке и история ответов.

Здесь только контейнеры состояния. Правило, как это состояние меняется после
ответа (алгоритм SM-2), появится на этапе 4 в ``core/srs/`` — модель хранит
данные, алгоритм задаёт поведение.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from qlizmet.core.clock import utcnow


@dataclass(slots=True)
class CardProgress:
    """Состояние интервального повторения для одной карточки (один пользователь)."""

    card_id: str
    ease: float = 2.5
    interval_days: int = 0
    repetitions: int = 0
    lapses: int = 0
    due_at: datetime | None = None
    last_reviewed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.ease <= 0:
            raise ValueError("ease должен быть положительным")
        if self.interval_days < 0:
            raise ValueError("interval_days не может быть отрицательным")
        if self.repetitions < 0:
            raise ValueError("repetitions не может быть отрицательным")
        if self.lapses < 0:
            raise ValueError("lapses не может быть отрицательным")

    @classmethod
    def new(cls, card_id: str) -> "CardProgress":
        """Прогресс для новой, ещё ни разу не показанной карточки."""
        return cls(card_id=card_id)

    def is_due(self, now: datetime | None = None) -> bool:
        """Пора ли повторять. Новая карточка (``due_at is None``) считается готовой."""
        if self.due_at is None:
            return True
        return self.due_at <= (now or utcnow())


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    """Один зафиксированный ответ. Неизменяемое событие для статистики и SRS."""

    card_id: str
    reviewed_at: datetime
    mode: str
    is_correct: bool
    quality: int | None = None
    response_ms: int | None = None
    user_answer: str | None = None

    def __post_init__(self) -> None:
        if self.quality is not None and not 0 <= self.quality <= 5:
            raise ValueError("quality должно быть в диапазоне 0..5")
        if self.response_ms is not None and self.response_ms < 0:
            raise ValueError("response_ms не может быть отрицательным")