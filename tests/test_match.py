"""Тесты игры Match."""
import random

import pytest

from qlizmet.core.models import Card, CardFace
from qlizmet.core.study import MatchGame, MatchOutcome, TileSide


def _card(front: str, back: str) -> Card:
    return Card.create(CardFace.from_text(front), CardFace.from_text(back))


def _deck():
    return [
        _card("Франция", "Париж"),
        _card("Италия", "Рим"),
        _card("Испания", "Мадрид"),
    ]


def _rng():
    return random.Random(0)


def test_board_has_two_tiles_per_card() -> None:
    cards = _deck()
    game = MatchGame(cards, rng=_rng())
    assert len(game.tiles) == 2 * len(cards)
    sides = {(t.card_id, t.side) for t in game.tiles}
    assert (cards[0].id, TileSide.FRONT) in sides
    assert (cards[0].id, TileSide.BACK) in sides


def test_pairs_limit() -> None:
    game = MatchGame(_deck(), pairs=2, rng=_rng())
    assert len(game.tiles) == 4
    assert game.summary().pairs == 2


def test_first_pick_then_match_removes_tiles() -> None:
    card = _card("Франция", "Париж")
    game = MatchGame([card, _card("Италия", "Рим")], rng=_rng())

    first = game.select(f"{card.id}:front")
    assert first.outcome is MatchOutcome.FIRST_PICK
    assert game.selected == f"{card.id}:front"

    second = game.select(f"{card.id}:back")
    assert second.outcome is MatchOutcome.MATCH
    assert game.matched == 1
    assert game.selected is None
    assert len(game.tiles) == 2  # осталась вторая пара


def test_mismatch_keeps_tiles() -> None:
    a = _card("Франция", "Париж")
    b = _card("Италия", "Рим")
    game = MatchGame([a, b], rng=_rng())

    game.select(f"{a.id}:front")
    fb = game.select(f"{b.id}:back")
    assert fb.outcome is MatchOutcome.MISMATCH
    assert game.mismatches == 1
    assert len(game.tiles) == 4  # ничего не убрали


def test_deselect_same_tile() -> None:
    a = _card("Франция", "Париж")
    game = MatchGame([a, _card("Италия", "Рим")], rng=_rng())
    game.select(f"{a.id}:front")
    fb = game.select(f"{a.id}:front")
    assert fb.outcome is MatchOutcome.DESELECT
    assert game.selected is None


def test_clearing_board_finishes_game() -> None:
    a = _card("Франция", "Париж")
    game = MatchGame([a], rng=_rng())
    game.select(f"{a.id}:front")
    game.select(f"{a.id}:back")
    assert game.is_finished
    assert game.matched == 1


def test_select_unknown_tile_raises() -> None:
    game = MatchGame([_card("Франция", "Париж")], rng=_rng())
    with pytest.raises(ValueError):
        game.select("нет-такой")


def test_select_after_finish_raises() -> None:
    a = _card("Франция", "Париж")
    game = MatchGame([a], rng=_rng())
    game.select(f"{a.id}:front")
    game.select(f"{a.id}:back")
    with pytest.raises(RuntimeError):
        game.select(f"{a.id}:front")


def test_shuffle_deterministic_with_seed() -> None:
    cards = _deck()
    order_a = [t.id for t in MatchGame(cards, rng=random.Random(5)).tiles]
    order_b = [t.id for t in MatchGame(cards, rng=random.Random(5)).tiles]
    assert order_a == order_b