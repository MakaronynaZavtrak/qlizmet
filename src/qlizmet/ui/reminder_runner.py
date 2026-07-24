"""Периодическая проверка: не пора ли напомнить о повторении.

Таймер лишь дёргает публичный ``check`` — сам он ничего не решает. Решение
принимает чистая логика из ``core.reminders``, а показывает уведомление
переданный «уведомитель» (в приложении это значок в трее). Благодаря такому
разделению поведение проверяется тестами без ожидания реального времени.

Про время: расписание SM-2 живёт в UTC, а тихие часы — понятие бытовое, «не
раньше девяти утра» означает девять утра **по местным часам**. Поэтому здесь
берётся локальное время, а не ``utcnow``.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from PySide6.QtCore import QObject, QTimer, Signal

from qlizmet.app.scheduler_service import SchedulerService
from qlizmet.app.settings import load_settings, save_settings
from qlizmet.core.reminders import ReminderDecision, ReminderPolicy, decide
from qlizmet.core.srs import PendingCounts

#: Как часто заглядывать. Правила внутри всё равно не дадут напомнить дважды,
#: поэтому частые проверки безвредны — зато напоминание не опоздает на полдня.
DEFAULT_INTERVAL_MS = 30 * 60 * 1000
#: Первая проверка вскоре после запуска, а не через полчаса.
STARTUP_DELAY_MS = 60 * 1000

REASON_BUSY = "приложение и так открыто"


class ReminderRunner(QObject):
    """Следит за временем и показывает напоминания."""

    notified = Signal(str, str)
    pending_changed = Signal(object)

    def __init__(
        self,
        scheduler: SchedulerService,
        notifier,
        *,
        is_busy: Callable[[], bool] | None = None,
        interval_ms: int = DEFAULT_INTERVAL_MS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._scheduler = scheduler
        self._notifier = notifier
        self._is_busy = is_busy

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.check)

        self._startup = QTimer(self)
        self._startup.setSingleShot(True)
        self._startup.setInterval(STARTUP_DELAY_MS)
        self._startup.timeout.connect(self.check)

    def start(self) -> None:
        self._timer.start()
        self._startup.start()

    def stop(self) -> None:
        self._timer.stop()
        self._startup.stop()

    @property
    def is_running(self) -> bool:
        return self._timer.isActive()

    def check(self, *, now: datetime | None = None) -> ReminderDecision:
        """Посмотреть, не пора ли напомнить, и напомнить, если пора.

        ``now`` — местное время: по нему считаются тихие часы и дата
        напоминания. Планировщику тот же момент передаётся в UTC, иначе
        «что просрочено» и «который час» разъехались бы по разным шкалам.
        """
        moment = now or datetime.now()
        pending = self._scheduler.total_pending(now=_as_utc(moment))
        self.pending_changed.emit(pending)

        if self._is_busy is not None and self._is_busy():
            # человек смотрит на приложение — уведомление было бы издевательством
            return ReminderDecision.skip(REASON_BUSY)

        settings = load_settings()
        decision = decide(
            pending,
            now=moment,
            last_sent=settings.last_reminder,
            policy=ReminderPolicy(enabled=settings.reminders_enabled),
        )
        if decision.should_notify:
            self._notifier.notify(decision.title, decision.body)
            save_settings(settings.with_reminder_sent(moment.date()))
            self.notified.emit(decision.title, decision.body)
        return decision

    def current_pending(self) -> PendingCounts:
        return self._scheduler.total_pending()


def _as_utc(moment: datetime) -> datetime:
    """Тот же момент в UTC. Время без часового пояса считается местным."""
    if moment.tzinfo is None:
        moment = moment.astimezone()
    return moment.astimezone(timezone.utc)
