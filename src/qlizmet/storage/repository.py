"""Абстракции хранилища.

Ядро зависит от этих интерфейсов, а не от конкретной БД. Реализации (SQLite и
т.п.) появятся в ``storage/sqlite/`` и будут удовлетворять этим протоколам —
инверсия зависимостей, благодаря которой БД остаётся сменной деталью.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from qlizmet.core.models import CardProgress, Deck, ReviewRecord


@runtime_checkable
class DeckRepository(Protocol):
    """Хранилище наборов карточек (вместе с самими карточками)."""

    def save(self, deck: Deck) -> None: ...

    def get(self, deck_id: str) -> Deck | None: ...

    def list_deck_ids(self) -> list[str]: ...

    def delete(self, deck_id: str) -> bool: ...


@runtime_checkable
class ProgressRepository(Protocol):
    """Хранилище SRS-состояния карточек и истории ответов."""

    def save(self, progress: CardProgress) -> None: ...

    def get(self, card_id: str) -> CardProgress | None: ...

    def add_review(self, record: ReviewRecord) -> None: ...

    def reviews_for(self, card_id: str) -> list[ReviewRecord]: ...
