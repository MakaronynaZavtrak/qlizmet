"""Тесты расстояния Левенштейна."""
from qlizmet.core.grading import levenshtein


def test_identical_strings() -> None:
    assert levenshtein("kitten", "kitten") == 0


def test_empty_against_nonempty() -> None:
    assert levenshtein("", "abc") == 3
    assert levenshtein("abc", "") == 3


def test_single_substitution() -> None:
    assert levenshtein("kitten", "sitten") == 1


def test_classic_kitten_sitting() -> None:
    assert levenshtein("kitten", "sitting") == 3


def test_insertion_and_deletion() -> None:
    assert levenshtein("cat", "cats") == 1
    assert levenshtein("cats", "cat") == 1