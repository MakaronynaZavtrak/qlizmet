"""Правила напоминаний: когда напомнить и что написать.

Модуль чистый — ни Qt, ни системного трея, ни файлов. На вход приходит
состояние (сколько карточек ждёт, когда напоминали в прошлый раз, который час),
на выход — решение. Благодаря этому всё поведение проверяется обычными тестами,
а Qt-часть остаётся тонкой обёрткой, которая просто показывает готовый текст.

Главный принцип: напоминание, которое приходит некстати, выключают на второй
день. Поэтому правил четыре — не чаще раза в сутки, только когда есть что
делать, не в тихие часы и только если человек этого хочет.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from qlizmet.core.plurals import cards as cards_word
from qlizmet.core.plurals import new_cards as new_word
from qlizmet.core.srs import PendingCounts

#: По умолчанию не тревожим до утра и после позднего вечера.
DEFAULT_QUIET_BEFORE = 9
DEFAULT_QUIET_AFTER = 22

TITLE = "qlizmet"


@dataclass(frozen=True, slots=True)
class ReminderPolicy:
    """Настройки напоминаний."""

    enabled: bool = True
    quiet_before: int = DEFAULT_QUIET_BEFORE
    quiet_after: int = DEFAULT_QUIET_AFTER

    def is_quiet_hour(self, moment: datetime) -> bool:
        return not (self.quiet_before <= moment.hour < self.quiet_after)


@dataclass(frozen=True, slots=True)
class ReminderDecision:
    """Что решили: напоминать или нет, и почему."""

    should_notify: bool
    title: str = ""
    body: str = ""
    reason: str = ""

    @classmethod
    def skip(cls, reason: str) -> "ReminderDecision":
        return cls(False, reason=reason)


def compose_body(pending: PendingCounts) -> str:
    """Текст напоминания под конкретные числа."""
    due, new = pending.due, pending.new
    if due and new:
        return f"Пора повторить: {due} {cards_word(due)}. И ещё {new} {new_word(new)}."
    if due:
        return f"Пора повторить: {due} {cards_word(due)}."
    return f"Можно изучить {new} {new_word(new)} {cards_word(new)}."


def decide(
    pending: PendingCounts,
    *,
    now: datetime,
    last_sent: date | None = None,
    policy: ReminderPolicy | None = None,
) -> ReminderDecision:
    """Решить, показывать ли напоминание прямо сейчас."""
    rules = policy or ReminderPolicy()

    if not rules.enabled:
        return ReminderDecision.skip("напоминания выключены")
    if pending.is_empty:
        return ReminderDecision.skip("сегодня нечего повторять")
    if last_sent is not None and last_sent >= now.date():
        return ReminderDecision.skip("сегодня уже напоминали")
    if rules.is_quiet_hour(now):
        return ReminderDecision.skip("тихие часы")

    return ReminderDecision(True, title=TITLE, body=compose_body(pending))
