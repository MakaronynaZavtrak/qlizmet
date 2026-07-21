"""Игра «Gravity» — падающие термины (чистая логика).

Термин «падает», игрок печатает ответ. Верно — очки и рост уровня; неверный ответ
или ``miss()`` (термин достиг дна — это дёрнет интерфейс по таймауту) стоят жизни.
Игра кончается, когда жизни на нуле или термины закончились.

Реальное падение, скорость и секундомер — это интерфейс (этап 8). Здесь только
счёт, жизни, уровни и переходы состояния. Печатать можно лишь текстовый ответ,
поэтому карточки с картинкой/формулой на ответной стороне в игру не попадают.
"""
from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass

from qlizmet.core.grading import Grader, GradingOptions, split_alternatives
from qlizmet.core.models import Card, CardFace
from qlizmet.core.study.base import (
    Direction,
    answer_face,
    ordered_cards,
    prompt_face,
)

POINTS_BASE = 100
LEVEL_UP_EVERY = 5
STARTING_LIVES = 3


@dataclass(frozen=True, slots=True)
class GravityPrompt:
    card_id: str
    prompt: CardFace


@dataclass(frozen=True, slots=True)
class GravityFeedback:
    is_correct: bool
    correct_answer: CardFace
    score: int
    lives: int
    game_over: bool


@dataclass(frozen=True, slots=True)
class GravitySummary:
    score: int
    correct: int
    wrong: int
    missed: int
    lives_left: int


class GravityGame:
    """Автомат игры: очки, жизни, уровни и переходы по ответам/промахам."""

    def __init__(
        self,
        cards: Iterable[Card],
        *,
        direction: Direction = Direction.FRONT_TO_BACK,
        grading: GradingOptions | None = None,
        lives: int = STARTING_LIVES,
        shuffle: bool = True,
        rng: random.Random | None = None,
    ) -> None:
        self._direction = direction
        self._grading = grading or GradingOptions()
        self._rng = rng or random.Random()

        all_cards = ordered_cards(cards, shuffle=shuffle, rng=self._rng)
        eligible = [c for c in all_cards if answer_face(c, direction).is_plain_text]
        self._skipped = len(all_cards) - len(eligible)
        self._by_id = {c.id: c for c in eligible}
        self._queue: list[str] = [c.id for c in eligible]
        self._total = len(eligible)

        self._lives = lives
        self._score = 0
        self._correct = 0
        self._wrong = 0
        self._missed = 0

    @property
    def total(self) -> int:
        return self._total

    @property
    def skipped(self) -> int:
        return self._skipped

    @property
    def score(self) -> int:
        return self._score

    @property
    def lives(self) -> int:
        return max(self._lives, 0)

    @property
    def level(self) -> int:
        return 1 + self._correct // LEVEL_UP_EVERY

    @property
    def is_over(self) -> bool:
        return self._lives <= 0 or not self._queue

    def current(self) -> GravityPrompt | None:
        """Падающий термин или ``None``, если игра окончена."""
        if self.is_over:
            return None
        card = self._by_id[self._queue[0]]
        return GravityPrompt(card_id=card.id, prompt=prompt_face(card, self._direction))

    def answer(self, text: str) -> GravityFeedback:
        card = self._require_current()
        answers = split_alternatives(answer_face(card, self._direction).plain_text)
        accepted = Grader(answers, self._grading).grade(text).is_accepted
        if accepted:
            self._score += POINTS_BASE * self.level  # очки по текущему уровню
            self._correct += 1
        else:
            self._wrong += 1
            self._lives -= 1
        self._queue.pop(0)
        return self._feedback(card, accepted)

    def miss(self) -> GravityFeedback:
        """Термин достиг дна (вызывает интерфейс по таймауту) — минус жизнь."""
        card = self._require_current()
        self._missed += 1
        self._lives -= 1
        self._queue.pop(0)
        return self._feedback(card, is_correct=False)

    def summary(self) -> GravitySummary:
        return GravitySummary(
            score=self._score,
            correct=self._correct,
            wrong=self._wrong,
            missed=self._missed,
            lives_left=self.lives,
        )

    def _require_current(self) -> Card:
        if self.is_over:
            raise RuntimeError("игра уже окончена")
        return self._by_id[self._queue[0]]

    def _feedback(self, card: Card, is_correct: bool) -> GravityFeedback:
        return GravityFeedback(
            is_correct=is_correct,
            correct_answer=answer_face(card, self._direction),
            score=self._score,
            lives=self.lives,
            game_over=self.is_over,
        )