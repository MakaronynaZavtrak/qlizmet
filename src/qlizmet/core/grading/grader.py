"""Оценка введённого ответа для режима Write.

Учитывает нормализацию, несколько допустимых ответов и устойчивость к опечаткам
(через расстояние Левенштейна). Отдельно поддержан жест «нет, я был прав».
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from enum import Enum

from qlizmet.core.grading.distance import levenshtein
from qlizmet.core.grading.normalization import NormalizationOptions, normalize


class Verdict(Enum):
    EXACT = "exact"          # точное совпадение после нормализации
    TYPO = "typo"            # принято, но с опечаткой (в пределах допуска)
    INCORRECT = "incorrect"


@dataclass(frozen=True, slots=True)
class GradingOptions:
    normalization: NormalizationOptions = field(default_factory=NormalizationOptions)
    typo_tolerance: bool = True


@dataclass(frozen=True, slots=True)
class GradingResult:
    verdict: Verdict
    matched_answer: str | None
    distance: int

    @property
    def is_accepted(self) -> bool:
        return self.verdict in (Verdict.EXACT, Verdict.TYPO)

    def as_overridden(self) -> "GradingResult":
        """Пользователь нажал «нет, я был прав» — засчитываем ответ как верный."""
        return replace(self, verdict=Verdict.EXACT)


class Grader:
    """Сравнивает введённый ответ с одним или несколькими допустимыми."""

    def __init__(
        self,
        accepted_answers: str | Sequence[str],
        options: GradingOptions | None = None,
    ) -> None:
        if isinstance(accepted_answers, str):
            accepted_answers = [accepted_answers]
        self.accepted = list(accepted_answers)
        self.options = options or GradingOptions()

    def grade(self, user_answer: str) -> GradingResult:
        norm = self.options.normalization
        user_norm = normalize(user_answer, norm)

        best_answer: str | None = None
        best_answer_norm = ""
        best_distance: int | None = None
        for answer in self.accepted:
            answer_norm = normalize(answer, norm)
            d = levenshtein(user_norm, answer_norm)
            if best_distance is None or d < best_distance:
                best_distance, best_answer, best_answer_norm = d, answer, answer_norm

        if best_distance is None:  # нет ни одного допустимого ответа
            return GradingResult(Verdict.INCORRECT, None, 0)

        if not user_norm:  # пустой ответ никогда не принимаем
            return GradingResult(Verdict.INCORRECT, None, best_distance)

        if best_distance == 0:
            return GradingResult(Verdict.EXACT, best_answer, 0)

        if self.options.typo_tolerance and best_distance <= _allowed_typos(
            len(best_answer_norm)
        ):
            return GradingResult(Verdict.TYPO, best_answer, best_distance)

        return GradingResult(Verdict.INCORRECT, None, best_distance)


def split_alternatives(text: str) -> list[str]:
    """Разбить строку допустимых ответов по разделителям ``/`` и ``;``."""
    parts = [chunk.strip() for chunk in text.replace(";", "/").split("/")]
    parts = [chunk for chunk in parts if chunk]
    return parts or [text.strip()]


def _allowed_typos(length: int) -> int:
    """Сколько правок прощаем при данной длине эталона."""
    if length <= 2:
        return 0
    if length <= 5:
        return 1
    return 2