"""Игра «Match» — сопоставление пар (чистая логика).

Из каждой карточки получаются две плитки — «лицо» и «оборот». Цель — убрать всё
поле, соединяя плитки одной карточки. Здесь только конечный автомат выбора и
совпадений; секундомер и анимация — это интерфейс (этап 8).
"""
from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from qlizmet.core.models import Card, CardFace


class TileSide(Enum):
    FRONT = "front"
    BACK = "back"


@dataclass(frozen=True, slots=True)
class MatchTile:
    id: str
    card_id: str
    side: TileSide
    face: CardFace


class MatchOutcome(Enum):
    FIRST_PICK = "first_pick"  # выбрали первую плитку, ждём вторую
    DESELECT = "deselect"      # сняли выбор с той же плитки
    MATCH = "match"            # пара совпала, плитки убраны
    MISMATCH = "mismatch"      # не совпало


@dataclass(frozen=True, slots=True)
class MatchFeedback:
    outcome: MatchOutcome
    tiles: tuple[str, ...]  # задействованные плитки (1 для first/deselect, 2 иначе)


@dataclass(frozen=True, slots=True)
class MatchSummary:
    pairs: int
    matched: int
    mismatches: int


class MatchGame:
    """Поле плиток и автомат сопоставления пар."""

    def __init__(
        self,
        cards: Iterable[Card],
        *,
        pairs: int | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._rng = rng or random.Random()
        card_list = list(cards)
        if pairs is not None:
            card_list = card_list[:pairs]

        tiles: list[MatchTile] = []
        for card in card_list:
            tiles.append(MatchTile(f"{card.id}:front", card.id, TileSide.FRONT, card.front))
            tiles.append(MatchTile(f"{card.id}:back", card.id, TileSide.BACK, card.back))
        self._rng.shuffle(tiles)

        self._tiles: dict[str, MatchTile] = {t.id: t for t in tiles}
        self._order: list[str] = [t.id for t in tiles]
        self._pairs = len(card_list)
        self._selected: str | None = None
        self._matched = 0
        self._mismatches = 0

    @property
    def tiles(self) -> tuple[MatchTile, ...]:
        """Плитки, оставшиеся на поле, в порядке раскладки."""
        return tuple(self._tiles[tid] for tid in self._order)

    @property
    def selected(self) -> str | None:
        return self._selected

    @property
    def matched(self) -> int:
        return self._matched

    @property
    def mismatches(self) -> int:
        return self._mismatches

    @property
    def is_finished(self) -> bool:
        return not self._order

    def select(self, tile_id: str) -> MatchFeedback:
        if self.is_finished:
            raise RuntimeError("игра уже окончена")
        if tile_id not in self._tiles:
            raise ValueError("нет такой плитки на поле")

        if self._selected is None:
            self._selected = tile_id
            return MatchFeedback(MatchOutcome.FIRST_PICK, (tile_id,))

        if tile_id == self._selected:
            self._selected = None
            return MatchFeedback(MatchOutcome.DESELECT, (tile_id,))

        first = self._tiles[self._selected]
        second = self._tiles[tile_id]
        pair = (first.id, second.id)
        self._selected = None

        if first.card_id == second.card_id and first.side is not second.side:
            self._remove(first.id)
            self._remove(second.id)
            self._matched += 1
            return MatchFeedback(MatchOutcome.MATCH, pair)

        self._mismatches += 1
        return MatchFeedback(MatchOutcome.MISMATCH, pair)

    def summary(self) -> MatchSummary:
        return MatchSummary(
            pairs=self._pairs, matched=self._matched, mismatches=self._mismatches
        )

    def _remove(self, tile_id: str) -> None:
        del self._tiles[tile_id]
        self._order.remove(tile_id)