"""Карточка и её стороны."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from qlizmet.core.clock import utcnow
from qlizmet.core.models.content import ContentBlock, TextBlock


@dataclass(frozen=True, slots=True)
class CardFace:
    """Одна сторона карточки — неизменяемая последовательность блоков."""

    blocks: tuple[ContentBlock, ...] = ()

    @classmethod
    def from_text(cls, text: str) -> "CardFace":
        """Удобный конструктор стороны из одного текстового блока."""
        return cls((TextBlock(text),))

    @property
    def is_empty(self) -> bool:
        return len(self.blocks) == 0

    @property
    def is_plain_text(self) -> bool:
        """True, если сторона состоит только из текста.

        Это и есть признак «пригодности» для режима Write: напечатать можно
        только текстовый ответ, но не картинку или формулу.
        """
        return len(self.blocks) > 0 and all(
            isinstance(block, TextBlock) for block in self.blocks
        )

    @property
    def plain_text(self) -> str:
        """Конкатенация текстовых блоков (для сравнения ответов и fallback-показа)."""
        return "".join(
            block.text for block in self.blocks if isinstance(block, TextBlock)
        )


@dataclass(slots=True)
class Card:
    """Карточка: лицевая и оборотная стороны плюс метаданные."""

    front: CardFace
    back: CardFace
    id: str = field(default_factory=lambda: uuid4().hex)
    tags: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=utcnow)
    modified_at: datetime = field(default_factory=utcnow)

    @classmethod
    def create(
        cls,
        front: CardFace,
        back: CardFace,
        tags: tuple[str, ...] = (),
        *,
        now: datetime | None = None,
    ) -> "Card":
        """Создать карточку с одинаковой меткой создания и изменения."""
        ts = now or utcnow()
        return cls(
            front=front,
            back=back,
            tags=tuple(tags),
            created_at=ts,
            modified_at=ts,
        )

    def touch(self, *, now: datetime | None = None) -> None:
        """Обновить метку последнего изменения."""
        self.modified_at = now or utcnow()