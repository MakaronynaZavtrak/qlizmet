"""Импорт и экспорт наборов в TSV (как у Quizlet: ``термин<TAB>определение``).

Формат текстовый, поэтому переносит только текстовое содержимое карточек. Картинки
и формулы через TSV не сохраняются — для полного переноса будет отдельный формат.
"""
from __future__ import annotations

from datetime import datetime

from qlizmet.core.models import Card, CardFace, Deck


def export_deck_to_tsv(deck: Deck) -> str:
    """Собрать набор в TSV. Каждая карточка — строка ``лицо<TAB>оборот``."""
    lines = []
    for card in deck.cards:
        term = _one_line(card.front.plain_text)
        definition = _one_line(card.back.plain_text)
        lines.append(f"{term}\t{definition}")
    return "\n".join(lines)


def import_deck_from_tsv(
    text: str,
    title: str,
    *,
    now: datetime | None = None,
) -> Deck:
    """Разобрать TSV в новый набор. Пустые строки и строки без табуляции пропускаются."""
    deck = Deck.create(title, now=now)
    for line in text.splitlines():
        term, sep, definition = line.partition("\t")
        if not sep or not term.strip():
            continue
        deck.add_card(
            Card.create(
                CardFace.from_text(term),
                CardFace.from_text(definition),
                now=now,
            ),
            now=now,
        )
    return deck


def _one_line(text: str) -> str:
    """Убрать табы и переводы строк, чтобы не поехала разметка TSV."""
    return text.replace("\t", " ").replace("\n", " ").replace("\r", " ")