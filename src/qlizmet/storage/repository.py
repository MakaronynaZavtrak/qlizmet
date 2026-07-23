"""Абстракции хранилища.

Ядро и прикладной слой зависят от этих протоколов, а не от конкретной БД.
Реализации на SQLite лежат в ``storage/sqlite/`` и удовлетворяют этим протоколам —
инверсия зависимостей, благодаря которой БД остаётся сменной деталью.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from qlizmet.core.models import CardProgress, Deck, ReviewRecord


@dataclass(frozen=True, slots=True)
class DeckSummary:
    """Строка списка наборов: только то, что нужно показать, без карточек."""

    id: str
    title: str
    description: str
    card_count: int


@runtime_checkable
class DeckRepository(Protocol):
    """Хранилище наборов карточек (вместе с самими карточками)."""

    def save(self, deck: Deck) -> None: ...

    def get(self, deck_id: str) -> Deck | None: ...

    def list_deck_ids(self) -> list[str]: ...

    def list_summaries(self) -> list[DeckSummary]: ...

    def delete(self, deck_id: str) -> bool: ...


@runtime_checkable
class ProgressRepository(Protocol):
    """Хранилище SRS-состояния карточек и истории ответов."""

    def save(self, progress: CardProgress) -> None: ...

    def get(self, card_id: str) -> CardProgress | None: ...

    def add_review(self, record: ReviewRecord) -> None: ...

    def reviews_for(self, card_id: str) -> list[ReviewRecord]: ...

    def progress_for(self, card_ids: Sequence[str]) -> dict[str, CardProgress]: ...

    def review_totals(self, card_ids: Sequence[str]) -> tuple[int, int]: ...
