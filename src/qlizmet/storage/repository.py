"""Абстракции хранилища.

Ядро зависит от этих интерфейсов, а не от конкретной БД. Реализации (SQLite и
т.п.) появятся в ``storage/sqlite/`` и будут удовлетворять этим протоколам —
инверсия зависимостей, благодаря которой БД остаётся сменной деталью.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DeckRepository(Protocol):
    """Хранилище наборов карточек."""

    def list_deck_ids(self) -> list[str]:
        """Вернуть идентификаторы всех сохранённых наборов."""
        ...
