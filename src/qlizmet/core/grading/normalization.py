"""Нормализация текста перед сравнением ответов.

Приводит две строки к сопоставимому виду: регистр, пробелы, пунктуация и (по
желанию) диакритика. Всё настраивается через ``NormalizationOptions``.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NormalizationOptions:
    ignore_case: bool = True
    collapse_whitespace: bool = True
    ignore_punctuation: bool = True
    strip_accents: bool = False


_DEFAULT = NormalizationOptions()


def normalize(text: str, options: NormalizationOptions = _DEFAULT) -> str:
    result = text
    if options.strip_accents:
        result = _strip_accents(result)
    if options.ignore_punctuation:
        result = "".join(ch for ch in result if not _is_punctuation(ch))
    if options.ignore_case:
        result = result.casefold()
    if options.collapse_whitespace:
        result = " ".join(result.split())
    else:
        result = result.strip()
    return result


def _is_punctuation(ch: str) -> bool:
    # Категории Unicode, начинающиеся с 'P', — это пунктуация.
    return unicodedata.category(ch).startswith("P")


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))