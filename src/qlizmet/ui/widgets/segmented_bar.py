"""Составная полоса: показывает соотношение нескольких величин.

Одна полоса вместо трёх отдельных чисел сразу отвечает на вопрос «сколько из
набора уже закреплено, а сколько ещё не тронуто». Цвета берутся из активной
темы, поэтому полоса переживает переключение светлой и тёмной.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QSizePolicy, QWidget

BAR_HEIGHT = 14
RADIUS = 7


@dataclass(frozen=True, slots=True)
class Segment:
    """Доля полосы: сколько единиц и каким цветом."""

    value: int
    color: str
    label: str = ""


class SegmentedBar(QWidget):
    """Полоса из нескольких долей, пропорциональных значениям."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("segmentedBar")
        self.setFixedHeight(BAR_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._segments: tuple[Segment, ...] = ()
        self._empty_color = "#888888"

    def set_segments(self, segments: list[Segment], *, empty_color: str) -> None:
        self._segments = tuple(s for s in segments if s.value > 0)
        self._empty_color = empty_color
        self.update()

    def segments(self) -> tuple[Segment, ...]:
        return self._segments

    @property
    def total(self) -> int:
        return sum(segment.value for segment in self._segments)

    def paintEvent(self, event) -> None:  # noqa: N802 - имя задано Qt
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # скругление применяем ко всей полосе, а доли рисуем внутри него
            full = QRectF(self.rect())
            clip = QPainterPath()
            clip.addRoundedRect(full, RADIUS, RADIUS)
            painter.setClipPath(clip)
            painter.fillRect(full, QColor(self._empty_color))

            total = self.total
            if total <= 0:
                return

            offset = 0.0
            for segment in self._segments:
                width = full.width() * segment.value / total
                painter.fillRect(
                    QRectF(full.left() + offset, full.top(), width, full.height()),
                    QColor(segment.color),
                )
                offset += width
        finally:
            painter.end()
