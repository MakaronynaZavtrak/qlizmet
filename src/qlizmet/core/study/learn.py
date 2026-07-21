"""Режим «Learn» — адаптивное заучивание.

Ведёт каждую карточку к состоянию «выучено». Логика:

* новая карточка спрашивается **выбором варианта** (узнавание);
* после первого верного ответа повышается до **ввода текста** (припоминание),
  если ответная сторона текстовая;
* ошибка на вводе демотирует карточку обратно к выбору (переучиваем);
* карточка «выучена» после ``mastery_threshold`` верных ответов подряд.

Интеграция с SM-2: если передать словарь прогресса, невыученные и «сложные»
(низкий ease) карточки идут первыми; каждый ответ отдаёт ``Grade`` — прикладной
слой скормит его ``review()`` (это коммит 5).
"""
from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from qlizmet.core.grading import Grader, GradingOptions, Verdict, split_alternatives
from qlizmet.core.models import Card, CardFace, CardProgress
from qlizmet.core.srs import Grade
from qlizmet.core.study.base import (
    Direction,
    answer_face,
    ordered_cards,
    prompt_face,
)


class QuestionType(Enum):
    CHOICE = "choice"     # выбор варианта
    WRITTEN = "written"   # ввод ответа


@dataclass(frozen=True, slots=True)
class LearnQuestion:
    """Текущий вопрос. Для CHOICE ``options`` заполнены, для WRITTEN — пусты."""

    type: QuestionType
    card_id: str
    prompt: CardFace
    options: tuple[CardFace, ...] = ()


@dataclass(frozen=True, slots=True)
class LearnFeedback:
    card_id: str
    is_correct: bool
    correct_answer: CardFace
    grade: Grade
    learned: bool


@dataclass(frozen=True, slots=True)
class LearnSummary:
    total: int
    learned: int
    questions_asked: int


class LearnSession:
    """Адаптивная сессия заучивания с очередью карточек."""

    def __init__(
        self,
        cards: Iterable[Card],
        *,
        direction: Direction = Direction.FRONT_TO_BACK,
        mastery_threshold: int = 2,
        choices: int = 4,
        grading: GradingOptions | None = None,
        progress: dict[str, CardProgress] | None = None,
        shuffle: bool = False,
        rng: random.Random | None = None,
    ) -> None:
        self._direction = direction
        self._threshold = mastery_threshold
        self._choices = choices
        self._grading = grading or GradingOptions()
        self._rng = rng or random.Random()

        initial = ordered_cards(cards, shuffle=shuffle, rng=self._rng)
        if progress:
            initial = _priority_order(initial, progress)

        self._all_cards = initial
        self._by_id = {card.id: card for card in initial}
        self._queue: list[str] = [card.id for card in initial]

        self._streak: dict[str, int] = {card.id: 0 for card in initial}
        self._seen_correct: set[str] = set()
        self._learned: set[str] = set()
        self._questions_asked = 0

        self._current_question: LearnQuestion | None = None
        self._current_id: str | None = None
        self._current_correct_index = -1

    @property
    def total(self) -> int:
        return len(self._all_cards)

    @property
    def learned_count(self) -> int:
        return len(self._learned)

    @property
    def is_finished(self) -> bool:
        return not self._queue

    def current(self) -> LearnQuestion | None:
        if not self._queue:
            return None
        if self._current_question is None:
            self._build_current()
        return self._current_question

    def answer_choice(self, index: int) -> LearnFeedback:
        question = self.current()
        if question is None:
            raise RuntimeError("сессия уже окончена")
        if question.type is not QuestionType.CHOICE:
            raise RuntimeError("текущий вопрос — с вводом ответа")
        is_correct = index == self._current_correct_index
        return self._process(is_correct, QuestionType.CHOICE, verdict=None)

    def answer_written(self, text: str) -> LearnFeedback:
        question = self.current()
        if question is None:
            raise RuntimeError("сессия уже окончена")
        if question.type is not QuestionType.WRITTEN:
            raise RuntimeError("текущий вопрос — с выбором варианта")
        card = self._by_id[question.card_id]
        answers = split_alternatives(answer_face(card, self._direction).plain_text)
        result = Grader(answers, self._grading).grade(text)
        return self._process(result.is_accepted, QuestionType.WRITTEN, result.verdict)

    def summary(self) -> LearnSummary:
        return LearnSummary(
            total=self.total,
            learned=self.learned_count,
            questions_asked=self._questions_asked,
        )


    def _build_current(self) -> None:
        card_id = self._queue[0]
        self._current_id = card_id
        card = self._by_id[card_id]
        can_write = answer_face(card, self._direction).is_plain_text
        if can_write and card_id in self._seen_correct:
            self._current_question = LearnQuestion(
                QuestionType.WRITTEN, card_id, prompt_face(card, self._direction)
            )
            self._current_correct_index = -1
        else:
            options, correct_index = self._build_options(card)
            self._current_question = LearnQuestion(
                QuestionType.CHOICE, card_id, prompt_face(card, self._direction), options
            )
            self._current_correct_index = correct_index

    def _build_options(self, card: Card) -> tuple[tuple[CardFace, ...], int]:
        correct = answer_face(card, self._direction)
        others = [c for c in self._all_cards if c.id != card.id]
        k = min(self._choices - 1, len(others))
        distractors = self._rng.sample(others, k) if k > 0 else []

        labelled = [(correct, True)] + [
            (answer_face(c, self._direction), False) for c in distractors
        ]
        self._rng.shuffle(labelled)
        options = tuple(face for face, _ in labelled)
        correct_index = next(i for i, (_, ok) in enumerate(labelled) if ok)
        return options, correct_index

    def _process(
        self,
        is_correct: bool,
        question_type: QuestionType,
        verdict: Verdict | None,
    ) -> LearnFeedback:
        card_id = self._current_id
        card = self._by_id[card_id]
        self._questions_asked += 1
        grade = _grade_for(question_type, is_correct, verdict)
        learned = False

        if is_correct:
            self._seen_correct.add(card_id)
            self._streak[card_id] += 1
            if self._streak[card_id] >= self._threshold:
                learned = True
                self._learned.add(card_id)
                self._queue.pop(0)
            else:
                self._queue.append(self._queue.pop(0))
        else:
            self._streak[card_id] = 0
            self._seen_correct.discard(card_id)  # демотируем обратно к выбору
            self._queue.append(self._queue.pop(0))

        self._current_question = None
        self._current_id = None
        return LearnFeedback(
            card_id=card_id,
            is_correct=is_correct,
            correct_answer=answer_face(card, self._direction),
            grade=grade,
            learned=learned,
        )


def _grade_for(
    question_type: QuestionType, is_correct: bool, verdict: Verdict | None
) -> Grade:
    if not is_correct:
        return Grade.AGAIN
    if question_type is QuestionType.WRITTEN and verdict is Verdict.TYPO:
        return Grade.HARD
    return Grade.GOOD


def _priority_order(
    cards: list[Card], progress: dict[str, CardProgress]
) -> list[Card]:
    """Невыученные (без прогресса) — вперёд, затем по возрастанию ease (сложные раньше)."""

    def key(card: Card) -> tuple[bool, float]:
        p = progress.get(card.id)
        return (p is not None, p.ease if p is not None else 0.0)

    return sorted(cards, key=key)