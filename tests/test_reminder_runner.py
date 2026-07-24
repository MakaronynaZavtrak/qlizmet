"""Тесты периодической проверки напоминаний.

Реального времени тесты не ждут: ``check`` — публичный метод, которому можно
передать любой момент, а таймер лишь дёргает его в приложении.
"""
from datetime import datetime, timedelta

import pytest

pytest.importorskip("PySide6")

from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.app.paths import ENV_HOME  # noqa: E402
from qlizmet.app.scheduler_service import SchedulerService  # noqa: E402
from qlizmet.app.settings import Settings, load_settings, save_settings  # noqa: E402
from qlizmet.app.study_service import StudyService  # noqa: E402
from qlizmet.core.srs import Grade  # noqa: E402
from qlizmet.storage.sqlite.repositories import (  # noqa: E402
    SqliteDeckRepository,
    SqliteProgressRepository,
)
from qlizmet.ui.reminder_runner import REASON_BUSY, ReminderRunner  # noqa: E402

MORNING = datetime(2026, 1, 10, 10, 0)
NIGHT = datetime(2026, 1, 10, 3, 0)


class FakeNotifier:
    """Заглушка вместо трея."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def notify(self, title: str, body: str) -> None:
        self.messages.append((title, body))


@pytest.fixture
def env(conn, tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    decks = SqliteDeckRepository(conn)
    progress = SqliteProgressRepository(conn)
    return (
        LibraryService(decks),
        progress,
        SchedulerService(decks, progress),
    )


def _runner(env, qt_app, *, is_busy=None) -> tuple[ReminderRunner, FakeNotifier]:
    _, _, scheduler = env
    notifier = FakeNotifier()
    return ReminderRunner(scheduler, notifier, is_busy=is_busy), notifier


# --- когда напоминаем ---


def test_notifies_when_cards_are_waiting(env, qt_app) -> None:
    library, _, _ = env
    library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")

    runner, notifier = _runner(env, qt_app)
    decision = runner.check(now=MORNING)

    assert decision.should_notify
    assert len(notifier.messages) == 1
    assert "2" in notifier.messages[0][1]


def test_silent_when_nothing_to_study(env, qt_app) -> None:
    library, progress, _ = env
    deck = library.import_tsv("Франция\tПариж", "Гео")
    StudyService(progress).record(deck.cards[0].id, Grade.GOOD, mode="write")

    runner, notifier = _runner(env, qt_app)
    assert not runner.check(now=MORNING).should_notify
    assert notifier.messages == []


def test_silent_at_night(env, qt_app) -> None:
    library, _, _ = env
    library.import_tsv("Франция\tПариж", "Гео")

    runner, notifier = _runner(env, qt_app)
    assert not runner.check(now=NIGHT).should_notify
    assert notifier.messages == []


def test_silent_while_app_is_in_use(env, qt_app) -> None:
    """Уведомлять человека, который смотрит в открытое приложение, незачем."""
    library, _, _ = env
    library.import_tsv("Франция\tПариж", "Гео")

    runner, notifier = _runner(env, qt_app, is_busy=lambda: True)
    decision = runner.check(now=MORNING)

    assert not decision.should_notify
    assert decision.reason == REASON_BUSY
    assert notifier.messages == []


def test_silent_when_disabled_in_settings(env, qt_app) -> None:
    library, _, _ = env
    library.import_tsv("Франция\tПариж", "Гео")
    save_settings(Settings(reminders_enabled=False))

    runner, notifier = _runner(env, qt_app)
    assert not runner.check(now=MORNING).should_notify


# --- не чаще раза в день ---


def test_second_check_same_day_is_silent(env, qt_app) -> None:
    library, _, _ = env
    library.import_tsv("Франция\tПариж", "Гео")

    runner, notifier = _runner(env, qt_app)
    runner.check(now=MORNING)
    runner.check(now=MORNING + timedelta(hours=2))

    assert len(notifier.messages) == 1


def test_next_day_notifies_again(env, qt_app) -> None:
    library, _, _ = env
    library.import_tsv("Франция\tПариж", "Гео")

    runner, notifier = _runner(env, qt_app)
    runner.check(now=MORNING)
    runner.check(now=MORNING + timedelta(days=1))

    assert len(notifier.messages) == 2


def test_notification_date_is_remembered(env, qt_app) -> None:
    library, _, _ = env
    library.import_tsv("Франция\tПариж", "Гео")

    runner, _ = _runner(env, qt_app)
    runner.check(now=MORNING)

    assert load_settings().last_reminder == MORNING.date()


def test_skipped_check_does_not_touch_settings(env, qt_app) -> None:
    library, _, _ = env
    library.import_tsv("Франция\tПариж", "Гео")

    runner, _ = _runner(env, qt_app)
    runner.check(now=NIGHT)

    assert load_settings().last_reminder is None


# --- счётчик и сигналы ---


def test_pending_is_reported_on_every_check(env, qt_app) -> None:
    library, _, _ = env
    library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")

    runner, _ = _runner(env, qt_app)
    seen = []
    runner.pending_changed.connect(seen.append)
    runner.check(now=NIGHT)  # даже когда напоминать нельзя

    assert seen and seen[0].total == 2


def test_notified_signal_carries_text(env, qt_app) -> None:
    library, _, _ = env
    library.import_tsv("Франция\tПариж", "Гео")

    runner, _ = _runner(env, qt_app)
    seen = []
    runner.notified.connect(lambda title, body: seen.append((title, body)))
    runner.check(now=MORNING)

    assert len(seen) == 1
    assert seen[0][1]


def test_schedule_and_clock_share_one_moment(env, qt_app) -> None:
    """«Что просрочено» и «который час» должны считаться от одного момента.

    Иначе напоминание смотрело бы на вчерашнее расписание сегодняшними глазами.
    """
    from datetime import timezone

    library, progress, _ = env
    deck = library.import_tsv("Франция\tПариж", "Гео")
    answered_at = MORNING.replace(hour=16).astimezone().astimezone(timezone.utc)
    StudyService(progress).record(
        deck.cards[0].id, Grade.GOOD, mode="write", now=answered_at
    )

    runner, notifier = _runner(env, qt_app)

    # на следующее утро сутки с момента ответа ещё не прошли
    assert not runner.check(now=MORNING + timedelta(days=1)).should_notify
    # а вечером — уже прошли
    assert runner.check(now=MORNING + timedelta(days=1, hours=7)).should_notify


# --- таймер ---


def test_start_and_stop(env, qt_app) -> None:
    runner, _ = _runner(env, qt_app)
    assert not runner.is_running

    runner.start()
    assert runner.is_running

    runner.stop()
    assert not runner.is_running


def test_current_pending(env, qt_app) -> None:
    library, _, _ = env
    library.import_tsv("Франция\tПариж\nИталия\tРим\nИспания\tМадрид", "Гео")

    runner, _ = _runner(env, qt_app)
    assert runner.current_pending().total == 3
