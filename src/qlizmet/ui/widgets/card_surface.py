"""Крупная карточка с анимацией переворота.

Контейнер со скруглением и рамкой, внутри которого живёт содержимое стороны.
Оформление задаёт тема (``#cardSurface``), здесь только поведение.

Переворот сделан «схлопыванием»: карточка сжимается по ширине до нуля, ровно в
середине содержимое подменяется, затем ширина возвращается — читается как
настоящий разворот. Всё движение описывает один параметр ``flipProgress``
(0 → 1), поэтому анимацию можно прокрутить покадрово и проверить тестами.

Важно про плавность: на время переворота карточка не ресайзится через лейаут
(это заставляло бы систему пересобирать компоновку и склеивать кадры — визуально
выходило рвано). Вместо этого мы один раз снимаем сторону в ``QPixmap`` и на
каждом кадре просто рисуем её сжатой по ширине. Такой кадр стоит доли
миллисекунды, поэтому переворот идёт плавно на полной частоте монитора.

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
    QRect,
    Qt,
    Signal,
)
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QSizePolicy, QVBoxLayout, QWidget

#: Полная длительность переворота (обе половины).
FLIP_MS = 380
MIN_CARD_WIDTH = 320
MIN_CARD_HEIGHT = 220


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
        self._swap_content: Callable[[], None] | None = None
        self._swapped = True

        self._content = content
        self._flipping = False
        self._snapshot: QPixmap | None = None  # снимок текущей стороны для кадра

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(content)
        self.setLayout(layout)

    # --- анимируемый параметр ---

    def _get_flip(self) -> float:
        return self._flip

    def _set_flip(self, value: float) -> None:
        # середина переворота: карточка «на ребре», самое время подменить сторону
        if value >= 0.5 and not self._swapped:
            self._swapped = True
            if self._swap_content is not None:
                self._swap_content()
            if self._flipping:
                self._snapshot = self._grab_card()  # снимок уже новой стороны
        self._flip = value
        if self._flipping:
            self.update()  # просто перерисовать сжатый снимок — это дёшево

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

        self._swap_content = swap_content
        self._swapped = False

        # замораживаем размер: содержимое на время переворота прячется, иначе
        # карточка схлопнулась бы по своему sizeHint и «прыгнула»
        self.setMinimumSize(self.size())
        self._snapshot = self._grab_card()  # снимок лица
        self._content.setVisible(False)
        self._flipping = True
        # на время переворота отключаем заливку фона: иначе тема залила бы фон
        # карточки на всю ширину и сжатие снимка было бы не видно. По бокам от
        # сжатого снимка просвечивает то, что за карточкой.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        animation = QPropertyAnimation(self, b"flipProgress", self)
        animation.setDuration(FLIP_MS)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        animation.finished.connect(self._finish)
        self._animation = animation
        animation.start()

    def stop_animation(self) -> None:
        """Прервать переворот и вернуть карточке нормальный вид."""
        if self._animation is not None:
            self._animation.stop()
            self._animation = None
        self._settle()

    # --- отрисовка кадра ---

    def paintEvent(self, event) -> None:  # noqa: N802 - имя задаёт Qt
        if not self._flipping or self._snapshot is None:
            super().paintEvent(event)
            return
        # сжатие по ширине: 1 → лицо во всю ширину, 0 → «ребро», снова 1 → оборот
        scale = abs(1.0 - 2.0 * self._flip)
        width = max(1, round(self.width() * scale))
        left = (self.width() - width) // 2
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(QRect(left, 0, width, self.height()), self._snapshot)
        painter.end()

    # --- внутреннее ---

    def _grab_card(self) -> QPixmap:
        """Снять карточку целиком (рамка + содержимое) в картинку.

        На время снимка выключаем режим переворота, показываем содержимое и
        возвращаем обычную заливку фона — иначе ``grab`` снял бы либо сам сжатый
        снимок, либо сторону без фона темы.
        """
        was_flipping = self._flipping
        was_styled = self.testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        was_nosys = self.testAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._flipping = False
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        self._content.setVisible(True)
        pixmap = self.grab()
        self._content.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, was_styled)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, was_nosys)
        self._flipping = was_flipping
        return pixmap

    def _finish(self) -> None:
        self._animation = None
        self._settle()
        self.flip_finished.emit()

    def _settle(self) -> None:
        """Досрочно завершить переворот: подменить сторону и вернуть обычный вид."""
        if not self._swapped:
            self._swapped = True
            if self._swap_content is not None:
                self._swap_content()
        self._flipping = False
        self._snapshot = None
        self._flip = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        self._content.setVisible(True)
        self.setMinimumSize(MIN_CARD_WIDTH, MIN_CARD_HEIGHT)
        self.update()
