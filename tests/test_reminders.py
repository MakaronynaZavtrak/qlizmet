"""Тесты склонения числительных и правил напоминаний."""
from datetime import date, datetime

import pytest

from qlizmet.core.plurals import cards, new_cards, plural
from qlizmet.core.reminders import (
    ReminderDecision,
    ReminderPolicy,
    compose_body,
    decide,
)
from qlizmet.core.srs import PendingCounts

NOON = datetime(2026, 1, 10, 12, 0)


# --- склонение ---


@pytest.mark.parametrize(
    "count, expected",
    [
        (1, "карточка"),
        (2, "карточки"),
        (3, "карточки"),
        (4, "карточки"),
        (5, "карточек"),
        (0, "карточек"),
        (21, "карточка"),
        (22, "карточки"),
        (25, "карточек"),
        (101, "карточка"),
    ],
)
def test_cards_plural(count, expected) -> None:
    assert cards(count) == expected


@pytest.mark.parametrize("count", [11, 12, 13, 14, 111, 112])
def test_teens_are_the_exception(count) -> None:
    """11–14 всегда требуют форму множественного числа, несмотря на последнюю цифру."""
    assert cards(count) == "карточек"


def test_new_cards_adjective() -> None:
    assert new_cards(1) == "новая"
    assert new_cards(3) == "новые"
    assert new_cards(7) == "новых"


def test_plural_is_generic() -> None:
    assert plural(1, "день", "дня", "дней") == "день"
    assert plural(3, "день", "дня", "дней") == "дня"
    assert plural(10, "день", "дня", "дней") == "дней"


# --- текст напоминания ---


def test_body_for_reviews_only() -> None:
    assert compose_body(PendingCounts(due=3)) == "Пора повторить: 3 карточки."


def test_body_for_new_only() -> None:
    assert "новые" in compose_body(PendingCounts(new=2))


def test_body_mentions_both_kinds() -> None:
    body = compose_body(PendingCounts(due=5, new=2))
    assert "5" in body
    assert "2" in body


def test_body_agrees_with_single_card() -> None:
    assert compose_body(PendingCounts(due=1)) == "Пора повторить: 1 карточка."


# --- правила ---


def test_notifies_when_there_is_work() -> None:
    decision = decide(PendingCounts(due=3), now=NOON)
    assert decision.should_notify
    assert decision.title
    assert decision.body


def test_silent_when_nothing_pending() -> None:
    decision = decide(PendingCounts(), now=NOON)
    assert not decision.should_notify
    assert "нечего" in decision.reason


def test_silent_when_disabled() -> None:
    decision = decide(
        PendingCounts(due=3), now=NOON, policy=ReminderPolicy(enabled=False)
    )
    assert not decision.should_notify


def test_only_once_per_day() -> None:
    decision = decide(PendingCounts(due=3), now=NOON, last_sent=date(2026, 1, 10))
    assert not decision.should_notify
    assert "уже напоминали" in decision.reason


def test_new_day_allows_another_reminder() -> None:
    decision = decide(PendingCounts(due=3), now=NOON, last_sent=date(2026, 1, 9))
    assert decision.should_notify


def test_quiet_at_night() -> None:
    night = datetime(2026, 1, 10, 3, 0)
    assert not decide(PendingCounts(due=3), now=night).should_notify


def test_quiet_late_evening() -> None:
    late = datetime(2026, 1, 10, 23, 30)
    assert not decide(PendingCounts(due=3), now=late).should_notify


def test_quiet_hours_are_configurable() -> None:
    early = datetime(2026, 1, 10, 7, 0)
    assert not decide(PendingCounts(due=3), now=early).should_notify

    owl = ReminderPolicy(quiet_before=6 * 60, quiet_after=23 * 60)
    assert decide(PendingCounts(due=3), now=early, policy=owl).should_notify


def test_boundaries_of_quiet_hours() -> None:
    policy = ReminderPolicy(quiet_before=9 * 60, quiet_after=22 * 60)
    assert not policy.is_quiet_hour(datetime(2026, 1, 10, 9, 0))   # ровно 9:00 — можно
    assert policy.is_quiet_hour(datetime(2026, 1, 10, 22, 0))      # ровно 22:00 — уже нет


def test_quiet_window_is_minute_precise() -> None:
    policy = ReminderPolicy(quiet_before=9 * 60 + 30, quiet_after=21 * 60 + 45)
    assert policy.is_quiet_hour(datetime(2026, 1, 10, 9, 29))      # до 9:30 — тихо
    assert not policy.is_quiet_hour(datetime(2026, 1, 10, 9, 30))  # с 9:30 — можно
    assert not policy.is_quiet_hour(datetime(2026, 1, 10, 21, 44)) # до 21:45 — можно
    assert policy.is_quiet_hour(datetime(2026, 1, 10, 21, 45))     # с 21:45 — тихо


def test_window_wraps_over_midnight() -> None:
    """С 16:01 до 16:00 — активно почти круглые сутки, тихо только [16:00, 16:01)."""
    policy = ReminderPolicy(quiet_before=16 * 60 + 1, quiet_after=16 * 60)
    assert not policy.is_quiet_hour(datetime(2026, 1, 10, 16, 1))   # начало окна
    assert not policy.is_quiet_hour(datetime(2026, 1, 10, 23, 0))   # вечер — активно
    assert not policy.is_quiet_hour(datetime(2026, 1, 10, 3, 0))    # ночь — активно
    assert not policy.is_quiet_hour(datetime(2026, 1, 10, 15, 59))  # до тихой минуты
    assert policy.is_quiet_hour(datetime(2026, 1, 10, 16, 0))       # ровно 16:00 — тихо


def test_same_start_and_end_is_all_day() -> None:
    policy = ReminderPolicy(quiet_before=16 * 60, quiet_after=16 * 60)
    assert not policy.is_quiet_hour(datetime(2026, 1, 10, 16, 0))
    assert not policy.is_quiet_hour(datetime(2026, 1, 10, 3, 0))
    assert not policy.is_quiet_hour(datetime(2026, 1, 10, 23, 59))


def test_disabled_wins_over_everything() -> None:
    """Выключенные напоминания молчат, даже когда работы много."""
    decision = decide(
        PendingCounts(due=50, new=50),
        now=NOON,
        policy=ReminderPolicy(enabled=False),
    )
    assert not decision.should_notify


def test_skip_decision_has_no_text() -> None:
    decision = ReminderDecision.skip("причина")
    assert not decision.should_notify
    assert decision.body == ""
