"""Прикладной use-case: что изучать сегодня.

Собирает план занятия из хранилища: какие карточки набора просрочены по
расписанию SM-2, а какие ещё ни разу не показывались. Как этот план превращается
в очередь — решает чистая логика в ``core.srs.scheduling``.
"""
from __future__ import annotations

from datetime import datetime

from qlizmet.core.clock import utcnow
from qlizmet.core.models import Card
from qlizmet.core.srs import PendingCounts, ReviewPlan
from qlizmet.storage.repository import DeckRepository, ProgressRepository


class SchedulerService:
    """План занятий по наборам."""

    def __init__(self, decks: DeckRepository, progress: ProgressRepository) -> None:
        self._decks = decks
        self._progress = progress

    def deck_plan(self, deck_id: str, *, now: datetime | None = None) -> ReviewPlan:
        """Что в этом наборе ждёт занятия прямо сейчас."""
        moment = now or utcnow()
        return ReviewPlan.of(
            due=self._progress.due_card_ids(deck_id, moment),
            new=self._progress.new_card_ids(deck_id),
        )

    def pending_by_deck(
        self, *, now: datetime | None = None
    ) -> dict[str, PendingCounts]:
        """Счётчики по всем наборам сразу — для значков в списке."""
        moment = now or utcnow()
        raw = self._progress.pending_counts_by_deck(moment)
        return {
            deck_id: PendingCounts(due=due, new=new)
            for deck_id, (due, new) in raw.items()
        }

    def total_pending(self, *, now: datetime | None = None) -> PendingCounts:
        """Сколько всего ждёт по всем наборам — пригодится для напоминаний."""
        counts = self.pending_by_deck(now=now).values()
        return PendingCounts(
            due=sum(c.due for c in counts),
            new=sum(c.new for c in counts),
        )

    def cards_for_session(
        self,
        deck_id: str,
        *,
        new_limit: int | None = None,
        now: datetime | None = None,
    ) -> list[Card]:
        """Карточки набора в порядке занятия: сначала повторы, затем новые.

        Порядок задаёт план, а сами карточки берутся из набора — так очередь
        остаётся списком идентификаторов до последнего момента.
        """
        deck = self._decks.get(deck_id)
        if deck is None:
            raise LookupError(f"набор не найден: {deck_id}")

        plan = self.deck_plan(deck_id, now=now)
        order = (
            plan.study_order()
            if new_limit is None
            else plan.study_order(new_limit=new_limit)
        )
        by_id = {card.id: card for card in deck.cards}
        return [by_id[card_id] for card_id in order if card_id in by_id]
