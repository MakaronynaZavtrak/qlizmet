"""Режим «Карточки» (Flashcards).

Самый простой режим: листаешь карточки, переворачиваешь, сам отмечаешь «знаю /
не знаю». Без оценки ввода и без SRS — это спокойный просмотр. Интервальные
повторения живут в режиме Learn.
"""
from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass

from qlizmet.core.models import Card, CardFace
from qlizmet.core.study.base import (
    Direction,
    answer_face,
    ordered_cards,
    prompt_face,
)


@dataclass(frozen=True, slots=True)
class FlashcardPrompt:
    """Текущая карточка на показе."""

    card_id: str
    prompt: CardFace
    answer: CardFace
    index: int   # 0-based позиция в сессии
    total: int


@dataclass(frozen=True, slots=True)
class FlashcardSummary:
    total: int
    reviewed: int
    known: int


class FlashcardSession:
    """Проход по колоде с самооценкой «знаю / не знаю»."""

    def __init__(
        self,
        cards: Iterable[Card],
        *,
        direction: Direction = Direction.FRONT_TO_BACK,
        shuffle: bool = False,
        rng: random.Random | None = None,
    ) -> None:
        self._cards = ordered_cards(cards, shuffle=shuffle, rng=rng)
        self._direction = direction
        self._index = 0
        self._reviewed = 0
        self._known = 0

    @property
    def total(self) -> int:
        return len(self._cards)

    @property
    def is_finished(self) -> bool:
        return self._index >= len(self._cards)

    def current(self) -> FlashcardPrompt | None:
        """Карточка на показе или ``None``, если сессия окончена."""
        if self.is_finished:
            return None
        card = self._cards[self._index]
        return FlashcardPrompt(
            card_id=card.id,
            prompt=prompt_face(card, self._direction),
            answer=answer_face(card, self._direction),
            index=self._index,
            total=self.total,
        )

    def mark(self, known: bool) -> None:
        """Отметить текущую карточку и перейти к следующей."""
        if self.is_finished:
            raise RuntimeError("сессия уже окончена")
        self._reviewed += 1
        if known:
            self._known += 1
        self._index += 1

    def summary(self) -> FlashcardSummary:
        return FlashcardSummary(
            total=self.total, reviewed=self._reviewed, known=self._known
        )