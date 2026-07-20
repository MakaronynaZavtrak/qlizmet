"""Тесты грейдера ответов."""
from qlizmet.core.grading import (
    Grader,
    GradingOptions,
    GradingResult,
    Verdict,
    split_alternatives,
)


def test_exact_match_after_normalization() -> None:
    result = Grader("Париж").grade("париж")
    assert result.verdict is Verdict.EXACT
    assert result.is_accepted
    assert result.distance == 0
    assert result.matched_answer == "Париж"


def test_small_typo_is_accepted() -> None:
    result = Grader("Париж").grade("Париш")  # ж → ш, одна опечатка
    assert result.verdict is Verdict.TYPO
    assert result.is_accepted
    assert result.distance == 1


def test_too_many_errors_rejected() -> None:
    result = Grader("кот").grade("пёс")
    assert result.verdict is Verdict.INCORRECT
    assert not result.is_accepted


def test_short_words_are_strict() -> None:
    # Для эталона длиной 2 опечаток не прощаем вовсе.
    result = Grader("мы").grade("ты")
    assert result.verdict is Verdict.INCORRECT


def test_multiple_accepted_answers() -> None:
    grader = Grader(["США", "USA", "United States"])
    result = grader.grade("usa")
    assert result.verdict is Verdict.EXACT
    assert result.matched_answer == "USA"


def test_multiple_answers_matches_the_long_one() -> None:
    grader = Grader(["США", "USA", "United States"])
    assert grader.grade("united states").matched_answer == "United States"


def test_empty_answer_is_incorrect() -> None:
    assert Grader("Париж").grade("   ").verdict is Verdict.INCORRECT


def test_typo_tolerance_can_be_disabled() -> None:
    strict = GradingOptions(typo_tolerance=False)
    result = Grader("Париж", strict).grade("Париш")
    assert result.verdict is Verdict.INCORRECT


def test_punctuation_ignored_in_grading() -> None:
    result = Grader("H2O").grade("h2o.")
    assert result.verdict is Verdict.EXACT


def test_override_marks_as_correct() -> None:
    rejected = Grader("кот").grade("пёс")
    assert not rejected.is_accepted
    overridden = rejected.as_overridden()
    assert overridden.verdict is Verdict.EXACT
    assert overridden.is_accepted


def test_split_alternatives() -> None:
    assert split_alternatives("США / USA ; United States") == [
        "США",
        "USA",
        "United States",
    ]


def test_split_alternatives_without_separators() -> None:
    assert split_alternatives("Париж") == ["Париж"]