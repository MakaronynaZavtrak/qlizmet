"""Тесты режима Test."""
import random

import pytest

from qlizmet.core.models import Card, CardFace, LatexBlock
from qlizmet.core.study import TestQuestionType, TestSession


def _card(front: str, back: str) -> Card:
    return Card.create(CardFace.from_text(front), CardFace.from_text(back))


PAIRS = [
    ("Франция", "Париж"),
    ("Италия", "Рим"),
    ("Испания", "Мадрид"),
    ("Германия", "Берлин"),
]


def _deck() -> list[Card]:
    return [_card(f, b) for f, b in PAIRS]


def _answer_map(cards: list[Card]) -> dict[str, str]:
    return {c.id: c.back.plain_text for c in cards}


def _rng() -> random.Random:
    return random.Random(0)


def test_one_question_per_card_capped_by_length() -> None:
    cards = _deck()
    assert TestSession(cards, length=3, rng=_rng()).total == 3
    assert TestSession(cards, length=10, rng=_rng()).total == 4


def test_restrict_to_written() -> None:
    session = TestSession(
        _deck(), question_types={TestQuestionType.WRITTEN}, rng=_rng()
    )
    assert all(q.type is TestQuestionType.WRITTEN for q in session.questions)


def test_restrict_to_choice_has_options() -> None:
    session = TestSession(
        _deck(), question_types={TestQuestionType.CHOICE}, rng=_rng()
    )
    assert all(q.type is TestQuestionType.CHOICE for q in session.questions)
    assert all(len(q.options) > 1 for q in session.questions)


def test_all_correct_choice_scores_full() -> None:
    cards = _deck()
    answers = _answer_map(cards)
    session = TestSession(cards, question_types={TestQuestionType.CHOICE}, rng=_rng())
    for i, q in enumerate(session.questions):
        correct_index = next(
            j for j, f in enumerate(q.options) if f.plain_text == answers[q.card_id]
        )
        session.answer(i, correct_index)
    result = session.grade()
    assert result.correct == result.total
    assert result.score == 1.0


def test_all_correct_true_false_scores_full() -> None:
    cards = _deck()
    answers = _answer_map(cards)
    session = TestSession(cards, question_types={TestQuestionType.TRUE_FALSE}, rng=_rng())
    for i, q in enumerate(session.questions):
        truth = q.statement.plain_text == answers[q.card_id]
        session.answer(i, truth)
    assert session.grade().score == 1.0


def test_all_correct_written_scores_full() -> None:
    cards = _deck()
    answers = _answer_map(cards)
    session = TestSession(cards, question_types={TestQuestionType.WRITTEN}, rng=_rng())
    for i, q in enumerate(session.questions):
        session.answer(i, answers[q.card_id])
    assert session.grade().score == 1.0


def test_unanswered_counts_as_incorrect() -> None:
    session = TestSession(_deck(), question_types={TestQuestionType.WRITTEN}, rng=_rng())
    result = session.grade()
    assert result.correct == 0
    assert result.total == 4


def test_wrong_response_type_raises() -> None:
    session = TestSession(_deck(), question_types={TestQuestionType.CHOICE}, rng=_rng())
    with pytest.raises(TypeError):
        session.answer(0, "строка вместо индекса")


def test_latex_answer_never_becomes_written() -> None:
    latex = Card.create(
        CardFace.from_text("производная sin x"), CardFace((LatexBlock(r"\cos x"),))
    )
    cards = [latex, *_deck()]
    session = TestSession(cards, question_types={TestQuestionType.WRITTEN}, rng=_rng())
    latex_question = next(q for q in session.questions if q.card_id == latex.id)
    assert latex_question.type is not TestQuestionType.WRITTEN


def test_partial_score() -> None:
    cards = _deck()
    answers = _answer_map(cards)
    session = TestSession(cards, question_types={TestQuestionType.WRITTEN}, rng=_rng())
    # отвечаем верно только на первый вопрос
    session.answer(0, answers[session.questions[0].card_id])
    result = session.grade()
    assert result.correct == 1
    assert result.score == pytest.approx(0.25)