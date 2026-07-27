"""Ротация карточек в подборе пар: новые пары каждый заход, проход по всему набору."""
import random

from qlizmet.core.models import Card, CardFace
from qlizmet.core.study import MatchRotation


def _deck(n: int) -> list[Card]:
    return [Card.create(CardFace.from_text(f"вопрос {i}"), CardFace.from_text(f"ответ {i}")) for i in range(n)]


def _ids(cards):
    return {card.id for card in cards}


def test_batch_respects_size() -> None:
    deck = _deck(7)
    rot = MatchRotation(deck, rng=random.Random(0))
    batch = rot.next_batch(6)
    assert len(batch) == 6


def test_cycles_through_all_cards() -> None:
    """За полный цикл каждая карточка показывается ровно раз (плюс возможный добор)."""
    deck = _deck(6)
    rot = MatchRotation(deck, rng=random.Random(1))
    first = rot.next_batch(3)
    second = rot.next_batch(3)
    assert _ids(first) | _ids(second) == _ids(deck)  # обе партии покрыли весь набор
    assert not (_ids(first) & _ids(second))          # без пересечений внутри цикла


def test_lone_leftover_is_padded_to_two() -> None:
    """7 карточек, партии по 6: остаётся одна — её дополняем уже виденной."""
    deck = _deck(7)
    rot = MatchRotation(deck, rng=random.Random(2))
    first = rot.next_batch(6)
    second = rot.next_batch(6)
    assert len(first) == 6
    assert len(second) == 2                    # одинокий хвост дополнен до пары
    leftover = (_ids(deck) - _ids(first)).pop()
    assert leftover in _ids(second)            # невиданная карточка вошла
    partner = (_ids(second) - {leftover}).pop()
    assert partner in _ids(first)              # добор — из уже показанных


def test_single_card_deck_shows_one_pair() -> None:
    deck = _deck(1)
    rot = MatchRotation(deck, rng=random.Random(3))
    batch = rot.next_batch(6)
    assert len(batch) == 1                      # одна карточка — одна пара, без добора


def test_two_card_deck_never_single() -> None:
    deck = _deck(2)
    rot = MatchRotation(deck, rng=random.Random(4))
    assert len(rot.next_batch(6)) == 2


def test_new_cycle_after_exhaustion() -> None:
    deck = _deck(4)
    rot = MatchRotation(deck, rng=random.Random(5))
    rot.next_batch(4)                           # весь набор за раз
    again = rot.next_batch(4)                   # цикл начинается заново
    assert _ids(again) == _ids(deck)


def test_empty_deck_yields_nothing() -> None:
    rot = MatchRotation([], rng=random.Random(6))
    assert rot.next_batch(6) == []
