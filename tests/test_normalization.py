"""Тесты нормализации текста."""
from qlizmet.core.grading import NormalizationOptions, normalize


def test_case_is_folded_by_default() -> None:
    assert normalize("ПариЖ") == "париж"


def test_whitespace_is_collapsed() -> None:
    assert normalize("  hello   world ") == "hello world"


def test_punctuation_is_removed_by_default() -> None:
    assert normalize("hello, world!") == "hello world"


def test_combined_normalization() -> None:
    assert normalize("Hello,  World!") == "hello world"


def test_accents_kept_by_default_preserves_cyrillic() -> None:
    # По умолчанию диакритику не трогаем, чтобы не сломать русский «й».
    assert normalize("йод") == "йод"


def test_strip_accents_when_enabled() -> None:
    opts = NormalizationOptions(strip_accents=True)
    assert normalize("café", opts) == "cafe"


def test_case_can_be_preserved() -> None:
    opts = NormalizationOptions(ignore_case=False)
    assert normalize("Париж", opts) == "Париж"