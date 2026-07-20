"""Алгоритм интервального повторения SM-2 (SuperMemo 2); на нём же построен Anki.

Чистая функция над состоянием: ``review`` принимает текущий ``CardProgress`` и
оценку ответа, а возвращает НОВЫЙ ``CardProgress`` — вход не меняется. Так модель
хранит состояние, а этот модуль задаёт поведение.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import IntEnum

from qlizmet.core.clock import utcnow
from qlizmet.core.models import CardProgress

INITIAL_EASE = 2.5
MIN_EASE = 1.3
FIRST_INTERVAL_DAYS = 1
SECOND_INTERVAL_DAYS = 6
PASSING_QUALITY = 3


class Grade(IntEnum):
    """Оценка ответа в стиле Anki. Значение элемента — это quality для SM-2 (0..5)."""

    AGAIN = 1  # не вспомнил → сброс
    HARD = 3   # вспомнил с трудом
    GOOD = 4   # вспомнил
    EASY = 5   # вспомнил легко


def review(
    progress: CardProgress,
    quality: int,
    *,
    now: datetime | None = None,
) -> CardProgress:
    """Пересчитать состояние карточки после ответа с оценкой ``quality`` (0..5).

    Возвращает новый ``CardProgress``; исходный объект не мутируется.
    """
    q = int(quality)
    if not 0 <= q <= 5:
        raise ValueError("quality должно быть в диапазоне 0..5")

    moment = now or utcnow()

    if q < PASSING_QUALITY:
        # Забыл: карточка снова «в изучении», интервал сбрасывается, засчитываем срыв.
        repetitions = 0
        interval_days = FIRST_INTERVAL_DAYS
        lapses = progress.lapses + 1
    else:
        # Интервал считается по СТАРОМУ ease; обновлённый ease влияет уже в следующий раз.
        if progress.repetitions == 0:
            interval_days = FIRST_INTERVAL_DAYS
        elif progress.repetitions == 1:
            interval_days = SECOND_INTERVAL_DAYS
        else:
            interval_days = round(progress.interval_days * progress.ease)
        repetitions = progress.repetitions + 1
        lapses = progress.lapses

    return CardProgress(
        card_id=progress.card_id,
        ease=_updated_ease(progress.ease, q),
        interval_days=interval_days,
        repetitions=repetitions,
        lapses=lapses,
        due_at=moment + timedelta(days=interval_days),
        last_reviewed_at=moment,
    )


def _updated_ease(ease: float, quality: int) -> float:
    """Обновить ease по формуле SM-2, не опуская ниже ``MIN_EASE``."""
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    return max(MIN_EASE, ease + delta)