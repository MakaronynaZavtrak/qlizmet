"""Общие детали для режимов обучения.

Тут только то, что действительно разделяют режимы: какая сторона карточки
показывается как вопрос, и в каком порядке идут карточки. Единого «интерфейса
режима» здесь нет намеренно — режимы слишком разные, чтобы их насильно свести
к одной форме (пошаговые Write/Learn и реал-тайм игры живут по-разному).
"""
from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from enum import Enum

from qlizmet.core.models import Card, CardFace


class Direction(Enum):
    """Какая сторона карточки является вопросом."""

    FRONT_TO_BACK = "front_to_back"
    BACK_TO_FRONT = "back_to_front"


def prompt_face(card: Card, direction: Direction) -> CardFace:
    """Сторона-вопрос при заданном направлении."""
    return card.front if direction is Direction.FRONT_TO_BACK else card.back


def answer_face(card: Card, direction: Direction) -> CardFace:
    """Сторона-ответ при заданном направлении."""
    return card.back if direction is Direction.FRONT_TO_BACK else card.front


def ordered_cards(
    cards: Iterable[Card],
    *,
    shuffle: bool = False,
    rng: random.Random | None = None,
) -> list[Card]:
    """Список карточек в порядке показа. При ``shuffle`` перемешивает копию.

    ``rng`` можно передать для детерминированного перемешивания в тестах.
    """
    result = list(cards)
    if shuffle:
        (rng or random).shuffle(result)
    return result