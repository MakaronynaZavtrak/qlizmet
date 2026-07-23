"""Прикладной use-case: статистика по набору.

Собирает воедино карточки из ``DeckRepository`` и прогресс с историей из
``ProgressRepository``, а сам подсчёт отдаёт чистой функции из ядра.
"""
from __future__ import annotations

from datetime import datetime

from qlizmet.core.stats import DeckStats, compute_deck_stats
from qlizmet.storage.repository import DeckRepository, ProgressRepository


class StatsService:
    """Сводка по набору для экрана статистики."""

    def __init__(self, decks: DeckRepository, progress: ProgressRepository) -> None:
        self._decks = decks
        self._progress = progress

    def deck_stats(self, deck_id: str, *, now: datetime | None = None) -> DeckStats:
        deck = self._decks.get(deck_id)
        if deck is None:
            raise LookupError(f"набор не найден: {deck_id}")

        card_ids = [card.id for card in deck.cards]
        states = self._progress.progress_for(card_ids)
        reviews, correct = self._progress.review_totals(card_ids)
        return compute_deck_stats(
            deck.cards, states, reviews=reviews, correct=correct, now=now
        )