"""Прикладной use-case: запись результата ответа.

``StudyService`` — точка, где встречаются три вещи: оценка ответа от режима
(``Grade``), алгоритм SM-2 (``review``) и хранилище (``ProgressRepository``).
На каждый ответ он загружает текущий прогресс карточки (или заводит новый),
пересчитывает его через SM-2, сохраняет и дописывает запись в историю.

Сервис знает только про интерфейс ``ProgressRepository`` и не зависит от
конкретного режима — Learn отдаёт ``Grade`` напрямую, а для Write вердикт
переводится в ``Grade`` через ``grade_from_verdict``.
"""
from __future__ import annotations

from datetime import datetime

from qlizmet.core.clock import utcnow
from qlizmet.core.grading import Verdict
from qlizmet.core.models import CardProgress, ReviewRecord
from qlizmet.core.srs import Grade, review
from qlizmet.core.srs.sm2 import PASSING_QUALITY
from qlizmet.storage.repository import ProgressRepository


class StudyService:
    """Записывает ответы: пересчитывает прогресс по SM-2 и сохраняет историю."""

    def __init__(self, progress: ProgressRepository) -> None:
        self._progress = progress

    def record(
        self,
        card_id: str,
        grade: Grade | int,
        *,
        mode: str,
        now: datetime | None = None,
        user_answer: str | None = None,
        response_ms: int | None = None,
    ) -> CardProgress:
        """Учесть один ответ и вернуть обновлённый прогресс карточки."""
        moment = now or utcnow()
        quality = int(grade)

        current = self._progress.get(card_id) or CardProgress.new(card_id)
        updated = review(current, quality, now=moment)
        self._progress.save(updated)
        self._progress.add_review(
            ReviewRecord(
                card_id=card_id,
                reviewed_at=moment,
                mode=mode,
                is_correct=quality >= PASSING_QUALITY,
                quality=quality,
                response_ms=response_ms,
                user_answer=user_answer,
            )
        )
        return updated


def grade_from_verdict(verdict: Verdict) -> Grade:
    """Перевести вердикт грейдера (режим Write) в оценку SM-2."""
    if verdict is Verdict.EXACT:
        return Grade.GOOD
    if verdict is Verdict.TYPO:
        return Grade.HARD
    return Grade.AGAIN