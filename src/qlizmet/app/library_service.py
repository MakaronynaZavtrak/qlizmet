"""Прикладной use-case: библиотека наборов.

Тонкая обёртка над ``DeckRepository`` для экрана со списком: перечислить, создать,
переименовать, удалить, импортировать из TSV. Интерфейс работает с этим сервисом
и ничего не знает ни про SQL, ни про то, где лежит база.
"""
from __future__ import annotations

from datetime import datetime

from qlizmet.core.models import Deck
from qlizmet.storage.import_export.tsv import export_deck_to_tsv, import_deck_from_tsv
from qlizmet.storage.repository import DeckRepository, DeckSummary


class LibraryService:
    """Операции над коллекцией наборов."""

    def __init__(self, decks: DeckRepository) -> None:
        self._decks = decks

    def summaries(self) -> list[DeckSummary]:
        """Список наборов для показа (без загрузки карточек)."""
        return self._decks.list_summaries()

    def get(self, deck_id: str) -> Deck | None:
        return self._decks.get(deck_id)

    def create(
        self,
        title: str,
        description: str = "",
        *,
        now: datetime | None = None,
    ) -> Deck:
        """Создать пустой набор. Пустое название не принимается."""
        clean = title.strip()
        if not clean:
            raise ValueError("название набора не может быть пустым")
        deck = Deck.create(clean, description.strip(), now=now)
        self._decks.save(deck)
        return deck

    def rename(
        self,
        deck_id: str,
        title: str,
        description: str | None = None,
        *,
        now: datetime | None = None,
    ) -> Deck:
        clean = title.strip()
        if not clean:
            raise ValueError("название набора не может быть пустым")
        deck = self._require(deck_id)
        deck.title = clean
        if description is not None:
            deck.description = description.strip()
        deck.touch(now=now)
        self._decks.save(deck)
        return deck

    def delete(self, deck_id: str) -> bool:
        return self._decks.delete(deck_id)

    def import_tsv(
        self,
        text: str,
        title: str,
        *,
        now: datetime | None = None,
    ) -> Deck:
        """Создать набор из TSV-текста (``термин<TAB>определение`` построчно)."""
        clean = title.strip()
        if not clean:
            raise ValueError("название набора не может быть пустым")
        deck = import_deck_from_tsv(text, clean, now=now)
        self._decks.save(deck)
        return deck

    def export_tsv(self, deck_id: str) -> str:
        return export_deck_to_tsv(self._require(deck_id))

    def _require(self, deck_id: str) -> Deck:
        deck = self._decks.get(deck_id)
        if deck is None:
            raise LookupError(f"набор не найден: {deck_id}")
        return deck