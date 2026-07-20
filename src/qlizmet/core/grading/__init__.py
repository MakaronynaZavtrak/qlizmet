"""Сравнение и оценка ответов пользователя (нормализация, расстояние, синонимы)."""
from qlizmet.core.grading.distance import levenshtein
from qlizmet.core.grading.grader import (
    Grader,
    GradingOptions,
    GradingResult,
    Verdict,
    split_alternatives,
)
from qlizmet.core.grading.normalization import NormalizationOptions, normalize

__all__ = [
    "normalize",
    "NormalizationOptions",
    "levenshtein",
    "Grader",
    "GradingOptions",
    "GradingResult",
    "Verdict",
    "split_alternatives",
]