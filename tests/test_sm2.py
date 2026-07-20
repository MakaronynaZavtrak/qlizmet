"""Тесты алгоритма SM-2."""
from datetime import datetime, timedelta, timezone

import pytest

from qlizmet.core.models import CardProgress
from qlizmet.core.srs import Grade, review
from qlizmet.core.srs.sm2 import MIN_EASE

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_first_two_intervals_are_fixed() -> None:
    p1 = review(CardProgress.new("c"), Grade.GOOD, now=NOW)
    assert p1.interval_days == 1
    assert p1.repetitions == 1

    p2 = review(p1, Grade.GOOD, now=NOW)
    assert p2.interval_days == 6
    assert p2.repetitions == 2


def test_expanding_interval_sequence_matches_ease() -> None:
    # При стабильном "Good" (q=4) ease не меняется, интервалы растут ×2.5.
    p = CardProgress.new("c")
    intervals = []
    for _ in range(5):
        p = review(p, Grade.GOOD, now=NOW)
        intervals.append(p.interval_days)
    assert intervals == [1, 6, 15, 38, 95]
    assert p.ease == pytest.approx(2.5)


def test_due_date_and_last_reviewed_are_set() -> None:
    p = review(CardProgress.new("c"), Grade.GOOD, now=NOW)
    assert p.last_reviewed_at == NOW
    assert p.due_at == NOW + timedelta(days=1)


def test_failure_resets_repetitions_and_counts_lapse() -> None:
    mature = CardProgress("c", ease=2.5, interval_days=15, repetitions=3)
    after = review(mature, Grade.AGAIN, now=NOW)
    assert after.interval_days == 1
    assert after.repetitions == 0
    assert after.lapses == 1
    assert after.due_at == NOW + timedelta(days=1)


def test_ease_never_drops_below_minimum() -> None:
    p = CardProgress("c", ease=1.4, interval_days=10, repetitions=3)
    for _ in range(5):
        p = review(p, Grade.AGAIN, now=NOW)
    assert p.ease == MIN_EASE


def test_ease_delta_by_quality() -> None:
    base = CardProgress("c", ease=2.5, interval_days=10, repetitions=3)
    assert review(base, 5, now=NOW).ease == pytest.approx(2.6)   # легко → ease растёт
    assert review(base, 4, now=NOW).ease == pytest.approx(2.5)   # норм → без изменений
    assert review(base, 3, now=NOW).ease == pytest.approx(2.36)  # трудно → падает


def test_interval_uses_old_ease_not_updated_one() -> None:
    # После q=5 ease станет 2.6, но интервал считается по старому 2.5.
    p = CardProgress("c", ease=2.5, interval_days=10, repetitions=2)
    after = review(p, 5, now=NOW)
    assert after.interval_days == round(10 * 2.5)   # 25, а не round(10*2.6)=26
    assert after.ease == pytest.approx(2.6)


def test_quality_out_of_range_raises() -> None:
    with pytest.raises(ValueError):
        review(CardProgress.new("c"), 6, now=NOW)


def test_input_progress_is_not_mutated() -> None:
    p = CardProgress.new("c")
    review(p, Grade.GOOD, now=NOW)
    assert p.interval_days == 0
    assert p.repetitions == 0
    assert p.due_at is None