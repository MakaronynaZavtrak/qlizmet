"""Тесты состояния прогресса и записи ответа."""
from datetime import datetime, timedelta, timezone

import pytest

from qlizmet.core.models import CardProgress, ReviewRecord


def test_new_progress_defaults() -> None:
    progress = CardProgress.new("card-1")
    assert progress.ease == 2.5
    assert progress.interval_days == 0
    assert progress.repetitions == 0
    assert progress.due_at is None


def test_new_card_is_due() -> None:
    progress = CardProgress.new("card-1")
    assert progress.is_due()


def test_due_check_respects_date() -> None:
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    progress = CardProgress("card-1", due_at=now + timedelta(days=1))
    assert not progress.is_due(now=now)
    assert progress.is_due(now=now + timedelta(days=2))


def test_invalid_ease_rejected() -> None:
    with pytest.raises(ValueError):
        CardProgress("card-1", ease=0)


def test_review_record_valid() -> None:
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    record = ReviewRecord(
        card_id="card-1",
        reviewed_at=now,
        mode="write",
        is_correct=True,
        quality=5,
        response_ms=1200,
        user_answer="Париж",
    )
    assert record.is_correct
    assert record.quality == 5


def test_review_record_rejects_bad_quality() -> None:
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        ReviewRecord(card_id="c", reviewed_at=now, mode="test", is_correct=False, quality=9)


def test_review_record_rejects_negative_time() -> None:
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        ReviewRecord(card_id="c", reviewed_at=now, mode="test", is_correct=True, response_ms=-5)