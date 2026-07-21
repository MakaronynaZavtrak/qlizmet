"""Тесты режима Write."""
import pytest

from qlizmet.core.models import Card, CardFace, LatexBlock, TextBlock
from qlizmet.core.study import Direction, WriteSession
from qlizmet.core.grading import Verdict as GradingVerdict


def _text_card(front: str, back: str) -> Card:
    return Card.create(CardFace.from_text(front), CardFace.from_text(back))


def _latex_answer_card() -> Card:
    return Card.create(
        CardFace.from_text("производная sin x"),
        CardFace((LatexBlock(r"\cos x"),)),
    )


def test_prompt_shows_question_side() -> None:
    session = WriteSession([_text_card("Франция", "Париж")])
    assert session.current().prompt.plain_text == "Франция"
    assert session.current().total == 1


def test_correct_answer_is_accepted() -> None:
    session = WriteSession([_text_card("Франция", "Париж")])
    feedback = session.submit("париж")
    assert feedback.is_accepted
    assert feedback.result.verdict is GradingVerdict.EXACT
    assert session.summary().correct == 1


def test_typo_is_accepted() -> None:
    session = WriteSession([_text_card("Франция", "Париж")])
    feedback = session.submit("Париш")
    assert feedback.is_accepted
    assert feedback.result.verdict is GradingVerdict.TYPO


def test_wrong_answer_reveals_correct_side() -> None:
    session = WriteSession([_text_card("Франция", "Париж")])
    feedback = session.submit("Лондон")
    assert not feedback.is_accepted
    assert feedback.answer.plain_text == "Париж"
    assert session.summary().incorrect == 1


def test_override_flips_last_to_correct() -> None:
    session = WriteSession([_text_card("Франция", "Париж")])
    session.submit("Лондон")
    updated = session.override_last()
    assert updated.is_accepted
    summary = session.summary()
    assert summary.correct == 1
    assert summary.incorrect == 0


def test_override_when_already_correct_is_noop() -> None:
    session = WriteSession([_text_card("Франция", "Париж")])
    session.submit("париж")
    session.override_last()
    assert session.summary().correct == 1
    assert session.summary().incorrect == 0


def test_alternatives_via_slash() -> None:
    session = WriteSession([_text_card("Штаты", "США/USA")])
    assert session.submit("usa").is_accepted


def test_non_text_answer_is_skipped() -> None:
    session = WriteSession([_text_card("Франция", "Париж"), _latex_answer_card()])
    assert session.total == 1
    assert session.skipped == 1


def test_back_to_front_direction() -> None:
    session = WriteSession(
        [_text_card("Франция", "Париж")], direction=Direction.BACK_TO_FRONT
    )
    assert session.current().prompt.plain_text == "Париж"
    assert session.submit("франция").is_accepted


def test_submit_after_finish_raises() -> None:
    session = WriteSession([_text_card("Франция", "Париж")])
    session.submit("париж")
    assert session.is_finished
    with pytest.raises(RuntimeError):
        session.submit("что-то")