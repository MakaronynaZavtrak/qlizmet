"""Тесты режима Learn."""
import random

import pytest

from qlizmet.core.models import Card, CardFace, CardProgress, LatexBlock
from qlizmet.core.srs import Grade
from qlizmet.core.study import LearnSession, QuestionType


def _card(front: str, back: str) -> Card:
    return Card.create(CardFace.from_text(front), CardFace.from_text(back))


def _deck(n: int) -> list[Card]:
    pairs = [
        ("Франция", "Париж"),
        ("Италия", "Рим"),
        ("Испания", "Мадрид"),
        ("Германия", "Берлин"),
    ]
    return [_card(f, b) for f, b in pairs[:n]]


def _rng() -> random.Random:
    return random.Random(0)


def test_new_card_starts_as_choice() -> None:
    session = LearnSession(_deck(4), rng=_rng())
    question = session.current()
    assert question.type is QuestionType.CHOICE
    assert len(question.options) == 4


def test_choice_has_a_correct_and_a_wrong_option() -> None:
    card = _card("Франция", "Париж")
    session = LearnSession([card, _card("Италия", "Рим")], rng=_rng())
    question = session.current()
    correct_index = next(
        i for i, f in enumerate(question.options) if f.plain_text == "Париж"
    )
    assert session.answer_choice(correct_index).is_correct
    # новая сессия, тот же seed — теперь отвечаем заведомо неверно
    session2 = LearnSession([card, _card("Италия", "Рим")], rng=_rng())
    wrong_index = next(
        i for i, f in enumerate(session2.current().options) if f.plain_text != "Париж"
    )
    assert not session2.answer_choice(wrong_index).is_correct


def test_escalates_to_written_after_first_correct() -> None:
    session = LearnSession([_card("Франция", "Париж")], rng=_rng())
    assert session.current().type is QuestionType.CHOICE
    session.answer_choice(0)  # единственный вариант — верный
    assert session.current().type is QuestionType.WRITTEN


def test_mastery_finishes_session() -> None:
    session = LearnSession([_card("Франция", "Париж")], mastery_threshold=2, rng=_rng())
    session.answer_choice(0)               # 1-й верный (choice)
    fb = session.answer_written("париж")   # 2-й верный (written) -> выучено
    assert fb.learned
    assert session.is_finished
    assert session.learned_count == 1


def test_wrong_written_resets_and_demotes_to_choice() -> None:
    session = LearnSession([_card("Франция", "Париж")], rng=_rng())
    session.answer_choice(0)                       # поднялись до written
    fb = session.answer_written("Лондон")          # ошибка
    assert not fb.is_correct
    assert fb.grade is Grade.AGAIN
    assert session.current().type is QuestionType.CHOICE  # демотирована обратно


def test_grade_mapping_for_written_typo_is_hard() -> None:
    session = LearnSession([_card("Франция", "Париж")], rng=_rng())
    session.answer_choice(0)
    fb = session.answer_written("Париш")  # опечатка — принято
    assert fb.is_correct
    assert fb.grade is Grade.HARD


def test_answer_written_on_choice_raises() -> None:
    session = LearnSession([_card("Франция", "Париж")], rng=_rng())
    assert session.current().type is QuestionType.CHOICE
    with pytest.raises(RuntimeError):
        session.answer_written("париж")


def test_latex_answer_stays_choice() -> None:
    card = Card.create(CardFace.from_text("производная sin x"), CardFace((LatexBlock(r"\cos x"),)))
    session = LearnSession([card, _card("Италия", "Рим")], rng=_rng())
    session.answer_choice(  # верный вариант — формульная грань (пустой plain_text)
        next(i for i, f in enumerate(session.current().options) if f.plain_text == "")
    )
    # даже после верного ответа формульная карточка не может стать written
    assert session.current().type is QuestionType.CHOICE


def test_priority_puts_unstudied_first() -> None:
    a = _card("A", "a")
    b = _card("B", "b")
    c = _card("C", "c")
    progress = {
        a.id: CardProgress(a.id, ease=2.5),
        b.id: CardProgress(b.id, ease=1.5),
        # c без прогресса
    }
    session = LearnSession([a, b, c], progress=progress, rng=_rng())
    assert session.current().card_id == c.id  # невыученная — первая


def test_summary_after_finish() -> None:
    session = LearnSession([_card("Франция", "Париж")], mastery_threshold=2, rng=_rng())
    session.answer_choice(0)
    session.answer_written("париж")
    summary = session.summary()
    assert summary.total == 1
    assert summary.learned == 1
    assert summary.questions_asked == 2