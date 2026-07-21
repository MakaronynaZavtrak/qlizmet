"""Тесты общих деталей режимов."""
import random

from qlizmet.core.models import Card, CardFace
from qlizmet.core.study import Direction, answer_face, ordered_cards, prompt_face


def _card(front: str, back: str) -> Card:
    return Card.create(CardFace.from_text(front), CardFace.from_text(back))


def test_prompt_and_answer_front_to_back() -> None:
    card = _card("Франция", "Париж")
    assert prompt_face(card, Direction.FRONT_TO_BACK).plain_text == "Франция"
    assert answer_face(card, Direction.FRONT_TO_BACK).plain_text == "Париж"


def test_prompt_and_answer_back_to_front() -> None:
    card = _card("Франция", "Париж")
    assert prompt_face(card, Direction.BACK_TO_FRONT).plain_text == "Париж"
    assert answer_face(card, Direction.BACK_TO_FRONT).plain_text == "Франция"


def test_ordered_cards_keeps_order_without_shuffle() -> None:
    cards = [_card(str(i), str(i)) for i in range(5)]
    assert ordered_cards(cards) == cards


def test_ordered_cards_shuffle_is_deterministic_with_seed() -> None:
    cards = [_card(str(i), str(i)) for i in range(10)]
    a = ordered_cards(cards, shuffle=True, rng=random.Random(42))
    b = ordered_cards(cards, shuffle=True, rng=random.Random(42))
    assert a == b
    assert set(id(c) for c in a) == set(id(c) for c in cards)  # тот же набор


def test_ordered_cards_does_not_mutate_input() -> None:
    cards = [_card(str(i), str(i)) for i in range(5)]
    original = list(cards)
    ordered_cards(cards, shuffle=True, rng=random.Random(1))
    assert cards == original