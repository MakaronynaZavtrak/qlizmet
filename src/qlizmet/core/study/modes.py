"""Перечень режимов и правила их доступности.

Не каждый режим работает с любым набором: печатать можно только текстовый ответ,
а игре на сопоставление нужна хотя бы пара карточек. Эти правила собраны здесь
как чистая логика — интерфейс лишь спрашивает, что можно запускать, и не
занимается самодеятельностью.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import Enum

from qlizmet.core.models import Card
from qlizmet.core.study.base import Direction, answer_face


class StudyMode(Enum):
    FLASHCARDS = "flashcards"
    LEARN = "learn"
    WRITE = "write"
    TEST = "test"
    MATCH = "match"
    GRAVITY = "gravity"

    @property
    def title(self) -> str:
        return _TITLES[self]


_TITLES = {
    StudyMode.FLASHCARDS: "Карточки",
    StudyMode.LEARN: "Заучивание",
    StudyMode.WRITE: "Письмо",
    StudyMode.TEST: "Тест",
    StudyMode.MATCH: "Подбор пар",
    StudyMode.GRAVITY: "Гравитация",
}

#: Режимам с выбором варианта нужен хотя бы один отвлекающий ответ.
MIN_CARDS_FOR_CHOICE = 2


def typed_answer_count(
    cards: Iterable[Card], direction: Direction = Direction.FRONT_TO_BACK
) -> int:
    """Сколько карточек можно спросить с вводом ответа."""
    return sum(1 for card in cards if answer_face(card, direction).is_plain_text)


def mode_availability(
    cards: Sequence[Card], direction: Direction = Direction.FRONT_TO_BACK
) -> dict[StudyMode, str | None]:
    """Для каждого режима — ``None``, если доступен, иначе причина отказа."""
    total = len(cards)
    typed = typed_answer_count(cards, direction)

    def need_cards(minimum: int) -> str | None:
        if total >= minimum:
            return None
        return f"нужно минимум {minimum} карт." if minimum > 1 else "нужна хотя бы одна карточка"

    def need_typed() -> str | None:
        if typed:
            return None
        return "нужен хотя бы один текстовый ответ"

    return {
        StudyMode.FLASHCARDS: need_cards(1),
        StudyMode.LEARN: need_cards(MIN_CARDS_FOR_CHOICE),
        StudyMode.WRITE: need_typed(),
        StudyMode.TEST: need_cards(MIN_CARDS_FOR_CHOICE),
        StudyMode.MATCH: need_cards(MIN_CARDS_FOR_CHOICE),
        StudyMode.GRAVITY: need_typed(),
    }


def available_modes(
    cards: Sequence[Card], direction: Direction = Direction.FRONT_TO_BACK
) -> set[StudyMode]:
    """Режимы, которые можно запустить на этом наборе."""
    return {
        mode for mode, reason in mode_availability(cards, direction).items()
        if reason is None
    }