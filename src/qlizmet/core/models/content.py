"""Блоки содержимого карточки.

Одна сторона карточки (``CardFace``) — это упорядоченная последовательность
блоков. Блок — неизменяемый value object одного из трёх типов: текст, формула
(LaTeX-выражение) или ссылка на изображение. Байты картинки здесь не хранятся —
только относительный путь в media-папке; так база не раздувается.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextBlock:
    """Простой текст."""

    text: str


@dataclass(frozen=True, slots=True)
class LatexBlock:
    """Математическое выражение в синтаксисе LaTeX (без ``$``-разделителей)."""

    latex: str

    def __post_init__(self) -> None:
        if not self.latex.strip():
            raise ValueError("LaTeX-выражение не может быть пустым")


@dataclass(frozen=True, slots=True)
class ImageBlock:
    """Ссылка на изображение в media-папке."""

    path: str
    alt: str = ""

    def __post_init__(self) -> None:
        if not self.path.strip():
            raise ValueError("путь к изображению не может быть пустым")


#: Любой допустимый блок содержимого.
ContentBlock = TextBlock | LatexBlock | ImageBlock