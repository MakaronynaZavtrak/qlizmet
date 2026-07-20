"""Набор карточек (агрегат)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from qlizmet.core.clock import utcnow
from qlizmet.core.models.card import Card


@dataclass(slots=True)
class Deck:
    """Набор — упорядоченный список карточек и точка входа для работы с ними."""

    title: str
    id: str = field(default_factory=lambda: uuid4().hex)
    description: str = ""
    cards: list[Card] = field(default_factory=list)
    created_at: datetime = field(default_factory=utcnow)
    modified_at: datetime = field(default_factory=utcnow)

    @classmethod
    def create(
        cls,
        title: str,
        description: str = "",
        *,
        now: datetime | None = None,
    ) -> "Deck":
        ts = now or utcnow()
        return cls(title=title, description=description, created_at=ts, modified_at=ts)

    def add_card(self, card: Card, *, now: datetime | None = None) -> None:
        self.cards.append(card)
        self.touch(now=now)

    def get_card(self, card_id: str) -> Card | None:
        return next((card for card in self.cards if card.id == card_id), None)

    def remove_card(self, card_id: str, *, now: datetime | None = None) -> bool:
        """Удалить карточку по id. Возвращает True, если карточка нашлась."""
        card = self.get_card(card_id)
        if card is None:
            return False
        self.cards.remove(card)
        self.touch(now=now)
        return True

    def touch(self, *, now: datetime | None = None) -> None:
        self.modified_at = now or utcnow()

    def __len__(self) -> int:
        return len(self.cards)

    def __iter__(self):
        return iter(self.cards)