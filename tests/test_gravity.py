"""Тесты игры Gravity."""
import random

import pytest

from qlizmet.core.models import Card, CardFace, LatexBlock
from qlizmet.core.study import GravityGame


def _card(front: str, back: str) -> Card:
    return Card.create(CardFace.from_text(front), CardFace.from_text(back))


def _deck(n: int) -> list[Card]:
    return [_card(f"term{i}", f"answer{i}") for i in range(n)]


def _answers(cards: list[Card]) -> dict[str, str]:
    return {c.id: c.back.plain_text for c in cards}


def _rng() -> random.Random:
    return random.Random(0)


def test_latex_answer_is_skipped() -> None:
    latex = Card.create(CardFace.from_text("sin"), CardFace((LatexBlock(r"\cos x"),)))
    game = GravityGame([latex, _card("Франция", "Париж")], rng=_rng())
    assert game.total == 1
    assert game.skipped == 1


def test_correct_answer_scores_and_advances() -> None:
    cards = _deck(2)
    answers = _answers(cards)
    game = GravityGame(cards, rng=_rng())
    first = game.current().card_id
    fb = game.answer(answers[first])
    assert fb.is_correct
    assert game.score == 100
    assert game.current().card_id != first


def test_wrong_answer_costs_a_life() -> None:
    cards = _deck(2)
    game = GravityGame(cards, lives=3, rng=_rng())
    fb = game.answer("заведомо неверно")
    assert not fb.is_correct
    assert game.lives == 2
    assert fb.correct_answer.plain_text.startswith("answer")


def test_miss_costs_a_life() -> None:
    cards = _deck(2)
    game = GravityGame(cards, lives=3, rng=_rng())
    game.miss()
    assert game.lives == 2
    assert game.summary().missed == 1


def test_game_over_when_lives_run_out() -> None:
    cards = _deck(5)
    game = GravityGame(cards, lives=2, rng=_rng())
    game.answer("нет")
    game.answer("нет")
    assert game.is_over
    assert game.current() is None
    with pytest.raises(RuntimeError):
        game.answer("нет")


def test_survive_all_terms_finishes() -> None:
    cards = _deck(3)
    answers = _answers(cards)
    game = GravityGame(cards, rng=_rng())
    while not game.is_over:
        game.answer(answers[game.current().card_id])
    assert game.is_over
    assert game.summary().correct == 3


def test_level_and_score_scale() -> None:
    cards = _deck(6)
    answers = _answers(cards)
    game = GravityGame(cards, lives=1, rng=_rng())
    for _ in range(6):
        game.answer(answers[game.current().card_id])
    # 5 верных на уровне 1 (по 100) + 1 на уровне 2 (200) = 700
    assert game.score == 700
    assert game.level == 2


def test_summary_fields() -> None:
    cards = _deck(3)
    answers = _answers(cards)
    game = GravityGame(cards, lives=3, rng=_rng())
    game.answer(answers[game.current().card_id])  # верно
    game.answer("нет")                             # неверно
    game.miss()                                    # промах
    summary = game.summary()
    assert summary.correct == 1
    assert summary.wrong == 1
    assert summary.missed == 1
    assert summary.lives_left == 1