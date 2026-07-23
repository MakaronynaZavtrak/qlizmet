"""Крупная карточка с анимацией переворота.

Контейнер со скруглением и рамкой, внутри которого живёт содержимое стороны.
Оформление задаёт тема (``#cardSurface``), здесь только поведение.

Переворот сделан «схлопыванием»: карточка сжимается по ширине до нуля, ровно в
середине содержимое подменяется, затем ширина возвращается — читается как
настоящий разворот. Всё движение описывает один параметр ``flipProgress``
(0 → 1), поэтому анимацию можно прокрутить покадрово и проверить тестами, не
дожидаясь реального времени.

Важно: на время переворота снимаются ограничения на минимальную ширину — иначе
карточка упёрлась бы в свой минимум и вместо анимации получилась бы подмена
кадра.

Анимация остаётся украшением: состояние переворота меняет вызывающий код сразу,
не дожидаясь её окончания.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import (
    Property,
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtWidgets import QFrame, QLayout, QSizePolicy, QVBoxLayout, QWidget

#: Полная длительность переворота (обе половины).
FLIP_MS = 340
MIN_CARD_WIDTH = 320
MIN_CARD_HEIGHT = 220
UNLIMITED = 16777215  # значение Qt для «без ограничения»


class CardSurface(QFrame):
    """Карточка: рамка, скругление и переворот содержимого."""

    flip_finished = Signal()

    def __init__(
        self,
        content: QWidget,
        *,
        animated: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("cardSurface")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumSize(MIN_CARD_WIDTH, MIN_CARD_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        self._animated = animated
        self._animation: QPropertyAnimation | None = None
        self._flip = 0.0
        self._full_width = MIN_CARD_WIDTH
        self._swap_content: Callable[[], None] | None = None
        self._swapped = True

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(content)
        self.setLayout(layout)

    # --- анимируемый параметр ---

    def _get_flip(self) -> float:
        return self._flip

    def _set_flip(self, value: float) -> None:
        self._flip = value
        # середина переворота: карточка «на ребре», самое время подменить сторону
        if value >= 0.5 and not self._swapped:
            self._swapped = True
            if self._swap_content is not None:
                self._swap_content()
        scale = abs(1.0 - 2.0 * value)
        self.setMaximumWidth(max(1, int(self._full_width * scale)))

    #: Ход переворота: 0 — лицо, 0.5 — ребро, 1 — оборот.
    flipProgress = Property(float, _get_flip, _set_flip)

    # --- поведение ---

    @property
    def is_animating(self) -> bool:
        return (
            self._animation is not None
            and self._animation.state() == QAbstractAnimation.State.Running
        )

    @property
    def animation(self) -> QPropertyAnimation | None:
        """Текущая анимация — нужна тестам, чтобы прокрутить её покадрово."""
        return self._animation

    def flip(self, swap_content: Callable[[], None]) -> None:
        """Перевернуть карточку, подменив содержимое в середине анимации."""
        if not self._animated:
            swap_content()
            self.flip_finished.emit()
            return

        if self._animation is not None:
            self._animation.stop()
            self._settle()

        self._full_width = max(self.width(), MIN_CARD_WIDTH)
        self._swap_content = swap_content
        self._swapped = False
        self._relax_limits()

        animation = QPropertyAnimation(self, b"flipProgress", self)
        animation.setDuration(FLIP_MS)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.finished.connect(self._finish)
        self._animation = animation
        animation.start()

    def stop_animation(self) -> None:
        """Прервать переворот и вернуть карточке нормальный вид."""
        if self._animation is not None:
            self._animation.stop()
            self._animation = None
        self._settle()

    # --- внутреннее ---

    def _finish(self) -> None:
        self._animation = None
        self._settle()
        self.flip_finished.emit()

    def _settle(self) -> None:
        """Досрочно завершить переворот: подменить сторону и снять сжатие."""
        if not self._swapped:
            self._swapped = True
            if self._swap_content is not None:
                self._swap_content()
        self._flip = 0.0
        self._restore_limits()

    def _relax_limits(self) -> None:
        self.setMinimumWidth(0)
        layout = self.layout()
        if layout is not None:
            layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

    def _restore_limits(self) -> None:
        self.setMaximumWidth(UNLIMITED)
        self.setMinimumWidth(MIN_CARD_WIDTH)
        layout = self.layout()
        if layout is not None:
            layout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
