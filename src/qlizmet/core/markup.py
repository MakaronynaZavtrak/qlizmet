"""Человеческая разметка граней карточки.

Набирать карточку через конструктор блоков неудобно, поэтому сторона карточки
редактируется как обычный текст с лёгкой разметкой:

* обычная строка — текст;
* ``$...$`` внутри строки — формула;
* строка вида ``![подпись](файл.png)`` — картинка.

Модуль намеренно чистый (без Qt): разбор и сборка — обычные функции, которые
полностью покрываются тестами без запуска интерфейса.
"""
from __future__ import annotations

import re

from qlizmet.core.models import CardFace, ContentBlock, ImageBlock, LatexBlock, TextBlock

_IMAGE_LINE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)\s*$")
_INLINE_MATH = re.compile(r"\$(?P<latex>[^$]+)\$")


def face_from_markup(text: str) -> CardFace:
    """Разобрать разметку в грань карточки."""
    blocks: list[ContentBlock] = []
    pending: list[str] = []

    def flush_text() -> None:
        if not pending:
            return
        merged = "\n".join(pending)
        pending.clear()
        if merged.strip():
            blocks.extend(_split_inline_math(merged))

    for line in text.splitlines():
        image = _IMAGE_LINE.match(line.strip())
        if image:
            flush_text()
            blocks.append(
                ImageBlock(image.group("path").strip(), image.group("alt").strip())
            )
        else:
            pending.append(line)
    flush_text()

    return CardFace(tuple(blocks))


def face_to_markup(face: CardFace) -> str:
    """Собрать разметку обратно из грани."""
    parts: list[str] = []
    for block in face.blocks:
        if isinstance(block, TextBlock):
            parts.append(block.text)
        elif isinstance(block, LatexBlock):
            parts.append(f"${block.latex}$")
        elif isinstance(block, ImageBlock):
            if parts and not parts[-1].endswith("\n"):
                parts.append("\n")
            parts.append(f"![{block.alt}]({block.path})\n")
    return "".join(parts).strip("\n")


def face_preview(face: CardFace, limit: int = 60) -> str:
    """Короткая однострочная выжимка грани для списков.

    Формулы и картинки текстом не покажешь, поэтому они обозначаются пометкой —
    иначе строка списка для карточки-картинки оказалась бы пустой.
    """
    chunks: list[str] = []
    for block in face.blocks:
        if isinstance(block, TextBlock):
            chunks.append(" ".join(block.text.split()))
        elif isinstance(block, LatexBlock):
            chunks.append(f"[формула: {block.latex}]")
        elif isinstance(block, ImageBlock):
            chunks.append(f"[картинка: {block.alt or block.path}]")
    preview = " ".join(chunk for chunk in chunks if chunk)
    if len(preview) > limit:
        preview = preview[: limit - 1].rstrip() + "…"
    return preview or "(пусто)"


def _split_inline_math(text: str) -> list[ContentBlock]:
    """Разбить строку на чередование текста и формул."""
    blocks: list[ContentBlock] = []
    position = 0
    for match in _INLINE_MATH.finditer(text):
        before = text[position : match.start()]
        if before:
            blocks.append(TextBlock(before))
        latex = match.group("latex").strip()
        if latex:
            blocks.append(LatexBlock(latex))
        position = match.end()

    tail = text[position:]
    if tail:
        blocks.append(TextBlock(tail))
    return blocks