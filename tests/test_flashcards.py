"""Тесты режима «Карточки»."""
import random

import pytest

from qlizmet.core.models import Card, CardFace
from qlizmet.core.study import Direction, FlashcardSession


def _deck_cards():
    return [
        Card.create(CardFace.from_text("Франция"), CardFace.from_text("Париж")),
        Card.create(CardFace.from_text("Италия"), CardFace.from_text("Рим")),
        Card.create(CardFace.from_text("Испания"), CardFace.from_text("Мадрид")),
    ]


def test_iterates_cards_in_order() -> None:
    session = FlashcardSession(_deck_cards())
    seen = []
    while not session.is_finished:
        seen.append(session.current().prompt.plain_text)
        session.mark(known=True)
    assert seen == ["Франция", "Италия", "Испания"]


def test_prompt_carries_index_and_total() -> None:
    session = FlashcardSession(_deck_cards())
    prompt = session.current()
    assert prompt.index == 0
    assert prompt.total == 3


def test_current_is_none_when_finished() -> None:
    session = FlashcardSession(_deck_cards())
    for _ in range(3):
        session.mark(known=True)
    assert session.is_finished
    assert session.current() is None


def test_summary_counts_known() -> None:
    session = FlashcardSession(_deck_cards())
    session.mark(known=True)
    session.mark(known=False)
    session.mark(known=True)
    summary = session.summary()
    assert summary.total == 3
    assert summary.reviewed == 3
    assert summary.known == 2


def test_mark_after_finish_raises() -> None:
    session = FlashcardSession(_deck_cards())
    for _ in range(3):
        session.mark(known=True)
    with pytest.raises(RuntimeError):
        session.mark(known=True)


def test_back_to_front_swaps_prompt_and_answer() -> None:
    session = FlashcardSession(_deck_cards(), direction=Direction.BACK_TO_FRONT)
    prompt = session.current()
    assert prompt.prompt.plain_text == "Париж"
    assert prompt.answer.plain_text == "Франция"


def test_shuffle_is_deterministic_with_seed() -> None:
    cards = _deck_cards()
    a = FlashcardSession(cards, shuffle=True, rng=random.Random(7))
    b = FlashcardSession(cards, shuffle=True, rng=random.Random(7))
    assert a.current().prompt.plain_text == b.current().prompt.plain_text