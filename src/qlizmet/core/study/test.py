"""Режим «Test» — экзамен фиксированной длины.

По одному вопросу на карточку, тип выбирается случайно из трёх: выбор варианта,
верно/неверно, ввод текста (с учётом доступности — печатать можно только
текстовый ответ). Вопросы генерируются сразу; пользователь отвечает на все, а
подсчёт очков идёт в конце. Правильные ответы хранятся отдельно от вопросов,
чтобы их нельзя было прочитать из «билета».
"""
from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from qlizmet.core.grading import Grader, GradingOptions, split_alternatives
from qlizmet.core.models import Card, CardFace
from qlizmet.core.study.base import (
    Direction,
    answer_face,
    ordered_cards,
    prompt_face,
)


class TestQuestionType(Enum):
    __test__ = False  # это доменный enum, а не тест-класс pytest

    CHOICE = "choice"          # выбор варианта
    TRUE_FALSE = "true_false"  # верно/неверно
    WRITTEN = "written"        # ввод ответа


@dataclass(frozen=True, slots=True)
class TestQuestion:
    """Вопрос билета (без правильного ответа)."""

    __test__ = False

    type: TestQuestionType
    card_id: str
    prompt: CardFace
    options: tuple[CardFace, ...] = ()   # для CHOICE
    statement: CardFace | None = None    # для TRUE_FALSE — показанный кандидат-ответ


@dataclass(frozen=True, slots=True)
class TestItemResult:
    __test__ = False

    card_id: str
    type: TestQuestionType
    is_correct: bool
    correct_answer: CardFace


@dataclass(frozen=True, slots=True)
class TestResult:
    __test__ = False

    total: int
    correct: int
    items: tuple[TestItemResult, ...]

    @property
    def score(self) -> float:
        return self.correct / self.total if self.total else 0.0


@dataclass(frozen=True, slots=True)
class _Key:
    type: TestQuestionType
    correct_index: int = -1
    is_true: bool = False
    accepted: tuple[str, ...] = ()


class TestSession:
    """Сгенерированный тест: билет + запись ответов + проверка в конце."""

    __test__ = False

    def __init__(
        self,
        cards: Iterable[Card],
        *,
        length: int = 20,
        direction: Direction = Direction.FRONT_TO_BACK,
        choices: int = 4,
        grading: GradingOptions | None = None,
        question_types: Iterable[TestQuestionType] | None = None,
        shuffle: bool = True,
        rng: random.Random | None = None,
    ) -> None:
        self._direction = direction
        self._choices = choices
        self._grading = grading or GradingOptions()
        self._rng = rng or random.Random()
        self._allowed = set(question_types) if question_types else set(TestQuestionType)

        pool = ordered_cards(cards, shuffle=shuffle, rng=self._rng)
        self._by_id = {card.id: card for card in pool}
        selected = pool[:length]

        self._questions: list[TestQuestion] = []
        self._keys: list[_Key] = []
        for card in selected:
            others = [c for c in pool if c.id != card.id]
            question, key = self._make_question(card, others)
            self._questions.append(question)
            self._keys.append(key)

        self._responses: dict[int, object] = {}

    @property
    def questions(self) -> tuple[TestQuestion, ...]:
        return tuple(self._questions)

    @property
    def total(self) -> int:
        return len(self._questions)

    def answer(self, index: int, response: object) -> None:
        """Записать ответ на вопрос ``index``.

        Тип ответа зависит от типа вопроса: int (выбор), bool (верно/неверно),
        str (ввод).
        """
        if not 0 <= index < len(self._questions):
            raise IndexError("нет вопроса с таким номером")
        q = self._questions[index]
        if q.type is TestQuestionType.CHOICE and not _is_int(response):
            raise TypeError("для выбора варианта нужен индекс (int)")
        if q.type is TestQuestionType.TRUE_FALSE and not isinstance(response, bool):
            raise TypeError("для верно/неверно нужен bool")
        if q.type is TestQuestionType.WRITTEN and not isinstance(response, str):
            raise TypeError("для ввода нужна строка")
        self._responses[index] = response

    def grade(self) -> TestResult:
        items: list[TestItemResult] = []
        correct = 0
        for i, (question, key) in enumerate(zip(self._questions, self._keys)):
            ok = self._check(key, self._responses.get(i))
            if ok:
                correct += 1
            items.append(
                TestItemResult(
                    card_id=question.card_id,
                    type=question.type,
                    is_correct=ok,
                    correct_answer=answer_face(
                        self._by_id[question.card_id], self._direction
                    ),
                )
            )
        return TestResult(total=len(self._questions), correct=correct, items=tuple(items))

    # --- внутреннее ---

    def _make_question(
        self, card: Card, others: list[Card]
    ) -> tuple[TestQuestion, _Key]:
        answer = answer_face(card, self._direction)
        kinds: list[TestQuestionType] = []
        if TestQuestionType.WRITTEN in self._allowed and answer.is_plain_text:
            kinds.append(TestQuestionType.WRITTEN)
        if others:
            if TestQuestionType.CHOICE in self._allowed:
                kinds.append(TestQuestionType.CHOICE)
            if TestQuestionType.TRUE_FALSE in self._allowed:
                kinds.append(TestQuestionType.TRUE_FALSE)
        if not kinds:  # запасной вариант, если ничего не подошло
            kinds.append(TestQuestionType.CHOICE)

        chosen = self._rng.choice(kinds)
        if chosen is TestQuestionType.WRITTEN:
            return self._written(card)
        if chosen is TestQuestionType.TRUE_FALSE:
            return self._true_false(card, others)
        return self._choice(card, others)

    def _choice(self, card: Card, others: list[Card]) -> tuple[TestQuestion, _Key]:
        correct = answer_face(card, self._direction)
        k = min(self._choices - 1, len(others))
        distractors = self._rng.sample(others, k) if k > 0 else []
        labelled = [(correct, True)] + [
            (answer_face(c, self._direction), False) for c in distractors
        ]
        self._rng.shuffle(labelled)
        options = tuple(face for face, _ in labelled)
        correct_index = next(i for i, (_, ok) in enumerate(labelled) if ok)
        question = TestQuestion(
            TestQuestionType.CHOICE, card.id, prompt_face(card, self._direction), options
        )
        return question, _Key(TestQuestionType.CHOICE, correct_index=correct_index)

    def _true_false(self, card: Card, others: list[Card]) -> tuple[TestQuestion, _Key]:
        correct = answer_face(card, self._direction)
        show_correct = self._rng.random() < 0.5 or not others
        if show_correct:
            statement = correct
        else:
            statement = answer_face(self._rng.choice(others), self._direction)
        is_true = statement == correct
        question = TestQuestion(
            TestQuestionType.TRUE_FALSE,
            card.id,
            prompt_face(card, self._direction),
            statement=statement,
        )
        return question, _Key(TestQuestionType.TRUE_FALSE, is_true=is_true)

    def _written(self, card: Card) -> tuple[TestQuestion, _Key]:
        accepted = tuple(
            split_alternatives(answer_face(card, self._direction).plain_text)
        )
        question = TestQuestion(
            TestQuestionType.WRITTEN, card.id, prompt_face(card, self._direction)
        )
        return question, _Key(TestQuestionType.WRITTEN, accepted=accepted)

    def _check(self, key: _Key, response: object) -> bool:
        if response is None:
            return False
        if key.type is TestQuestionType.CHOICE:
            return response == key.correct_index
        if key.type is TestQuestionType.TRUE_FALSE:
            return response == key.is_true
        if key.type is TestQuestionType.WRITTEN:
            return Grader(list(key.accepted), self._grading).grade(str(response)).is_accepted
        return False


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)