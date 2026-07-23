"""Прикладной use-case: редактирование карточек набора.

Операции над карточками внутри набора: добавить, изменить, удалить, переставить.
Каждая операция загружает набор, меняет его и сохраняет целиком — репозиторий
обновляет карточки по ``id``, поэтому прогресс и история уцелевших карточек не
теряются (см. ``SqliteDeckRepository.save``).
"""
from __future__ import annotations

from datetime import datetime

from qlizmet.core.models import Card, CardFace, Deck
from qlizmet.storage.repository import DeckRepository


class DeckService:
    """Правка содержимого одного набора."""

    def __init__(self, decks: DeckRepository) -> None:
        self._decks = decks

    def get(self, deck_id: str) -> Deck:
        return self._require(deck_id)

    def add_card(
        self,
        deck_id: str,
        front: CardFace,
        back: CardFace,
        tags: tuple[str, ...] = (),
        *,
        now: datetime | None = None,
    ) -> Card:
        if front.is_empty and back.is_empty:
            raise ValueError("карточка не может быть пустой с обеих сторон")
        deck = self._require(deck_id)
        card = Card.create(front, back, tags, now=now)
        deck.add_card(card, now=now)
        self._decks.save(deck)
        return card

    def update_card(
        self,
        deck_id: str,
        card_id: str,
        front: CardFace,
        back: CardFace,
        tags: tuple[str, ...] = (),
        *,
        now: datetime | None = None,
    ) -> Card:
        if front.is_empty and back.is_empty:
            raise ValueError("карточка не может быть пустой с обеих сторон")
        deck = self._require(deck_id)
        card = deck.get_card(card_id)
        if card is None:
            raise LookupError(f"карточка не найдена: {card_id}")

        card.front = front
        card.back = back
        card.tags = tuple(tags)
        card.touch(now=now)
        deck.touch(now=now)
        self._decks.save(deck)
        return card

    def delete_card(
        self, deck_id: str, card_id: str, *, now: datetime | None = None
    ) -> bool:
        deck = self._require(deck_id)
        removed = deck.remove_card(card_id, now=now)
        if removed:
            self._decks.save(deck)
        return removed

    def move_card(
        self, deck_id: str, card_id: str, offset: int, *, now: datetime | None = None
    ) -> bool:
        """Сдвинуть карточку в списке на ``offset`` позиций.

        Возвращает False, если карточки нет или двигать некуда (край списка).
        """
        deck = self._require(deck_id)
        card = deck.get_card(card_id)
        if card is None:
            return False

        index = deck.cards.index(card)
        target = index + offset
        if not 0 <= target < len(deck.cards):
            return False

        deck.cards.pop(index)
        deck.cards.insert(target, card)
        deck.touch(now=now)
        self._decks.save(deck)
        return True

    def _require(self, deck_id: str) -> Deck:
        deck = self._decks.get(deck_id)
        if deck is None:
            raise LookupError(f"набор не найден: {deck_id}")
        return deck