"""Режим «Write» — ввод ответа текстом.

Показывает сторону-вопрос, пользователь печатает ответ, грейдер с этапа 5 его
оценивает (точно / опечатка / неверно). Один проход по колоде; адаптивные
повторы — это уже режим Learn.

Печатать можно только текстовый ответ, поэтому карточки, у которых ответная
сторона — картинка или формула, в сессию не попадают (учитываются в ``skipped``).
"""
from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass

from qlizmet.core.grading import Grader, GradingOptions, GradingResult, split_alternatives
from qlizmet.core.models import Card, CardFace
from qlizmet.core.study.base import (
    Direction,
    answer_face,
    ordered_cards,
    prompt_face,
)


@dataclass(frozen=True, slots=True)
class WritePrompt:
    """Вопрос на показе (ответ ещё не раскрыт)."""

    card_id: str
    prompt: CardFace
    index: int
    total: int


@dataclass(frozen=True, slots=True)
class WriteFeedback:
    """Итог оценки одного ответа: вердикт и правильная сторона для показа."""

    result: GradingResult
    answer: CardFace

    @property
    def is_accepted(self) -> bool:
        return self.result.is_accepted


@dataclass(frozen=True, slots=True)
class WriteSummary:
    total: int
    correct: int
    incorrect: int
    skipped: int


class WriteSession:
    """Один проход: вопрос → ввод → оценка, с возможностью override последнего."""

    def __init__(
        self,
        cards: Iterable[Card],
        *,
        direction: Direction = Direction.FRONT_TO_BACK,
        grading: GradingOptions | None = None,
        shuffle: bool = False,
        rng: random.Random | None = None,
    ) -> None:
        self._direction = direction
        self._options = grading or GradingOptions()

        all_cards = ordered_cards(cards, shuffle=shuffle, rng=rng)
        # оставляем только те, где ответ можно напечатать (текстовая сторона)
        self._cards = [
            c for c in all_cards if answer_face(c, direction).is_plain_text
        ]
        self._skipped = len(all_cards) - len(self._cards)

        self._index = 0
        self._correct = 0
        self._incorrect = 0
        self._last: WriteFeedback | None = None
        self._last_accepted = False

    @property
    def total(self) -> int:
        return len(self._cards)

    @property
    def skipped(self) -> int:
        return self._skipped

    @property
    def is_finished(self) -> bool:
        return self._index >= len(self._cards)

    def current(self) -> WritePrompt | None:
        if self.is_finished:
            return None
        card = self._cards[self._index]
        return WritePrompt(
            card_id=card.id,
            prompt=prompt_face(card, self._direction),
            index=self._index,
            total=self.total,
        )

    def submit(self, user_answer: str) -> WriteFeedback:
        """Оценить ответ на текущую карточку и перейти к следующей."""
        if self.is_finished:
            raise RuntimeError("сессия уже окончена")
        card = self._cards[self._index]
        answers = split_alternatives(answer_face(card, self._direction).plain_text)
        result = Grader(answers, self._options).grade(user_answer)

        feedback = WriteFeedback(result=result, answer=answer_face(card, self._direction))
        if result.is_accepted:
            self._correct += 1
        else:
            self._incorrect += 1
        self._last = feedback
        self._last_accepted = result.is_accepted
        self._index += 1
        return feedback

    def override_last(self) -> WriteFeedback:
        """«Нет, я был прав» — засчитать последний ответ как верный."""
        if self._last is None:
            raise RuntimeError("ещё не было ни одного ответа")
        if self._last_accepted:
            return self._last  # уже засчитан верным — ничего не меняем
        self._incorrect -= 1
        self._correct += 1
        self._last = WriteFeedback(
            result=self._last.result.as_overridden(), answer=self._last.answer
        )
        self._last_accepted = True
        return self._last

    def summary(self) -> WriteSummary:
        return WriteSummary(
            total=self.total,
            correct=self._correct,
            incorrect=self._incorrect,
            skipped=self._skipped,
        )