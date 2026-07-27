"""Кнопка варианта ответа с переносом текста.

Обычный ``QPushButton`` текст не переносит — он его обрезает. Здесь внутри кнопки
живёт ``QLabel`` с переносом по словам: длинный ответ уходит на новую строку, а
кнопка растёт в высоту. Тот же виджет умеет показать вариант-формулу картинкой.

Клик остаётся кликом кнопки (наследуем ``QPushButton``), поэтому вызывающий код
подключается к обычному сигналу ``clicked``.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

MARGIN_X = 14
MARGIN_Y = 10
MIN_HEIGHT = 44


class ChoiceButton(QPushButton):
    """Кнопка варианта: переносит текст по словам либо показывает формулу."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = QLabel(self)
        self._label.setObjectName("choiceLabel")
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # клики по подписи должны доходить до самой кнопки
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_X, MARGIN_Y, MARGIN_X, MARGIN_Y)
        layout.addWidget(self._label)
        # по горизонтали кнопки делят строку поровну, по вертикали растут под текст
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding
        )

    def set_text(self, text: str) -> None:
        """Показать текстовый вариант (с переносом)."""
        self._label.setText(text)  # setText сбрасывает ранее заданную картинку

    def set_formula(self, pixmap: QPixmap) -> None:
        """Показать вариант-формулу картинкой."""
        self._label.setPixmap(pixmap)  # setPixmap сбрасывает ранее заданный текст

    def is_formula(self) -> bool:
        """Показана ли сейчас формула-картинка (для тестов)."""
        pixmap = self._label.pixmap()
        return pixmap is not None and not pixmap.isNull()

    def displayed_text(self) -> str:
        """Текущий текст на кнопке (пустой, если показана формула)."""
        return self._label.text()

    # высота кнопки должна следовать за перенесённым текстом при её ширине

    def hasHeightForWidth(self) -> bool:
        return self._label.pixmap() is None or self._label.pixmap().isNull()

    def heightForWidth(self, width: int) -> int:
        inner = max(1, width - 2 * MARGIN_X)
        height = self._label.heightForWidth(inner)
        if height < 0:
            height = self._label.sizeHint().height()
        return max(MIN_HEIGHT, height + 2 * MARGIN_Y)

    def sizeHint(self) -> QSize:
        base = super().sizeHint()
        width = self.width() or base.width()
        return QSize(base.width(), self.heightForWidth(width))

    def minimumSizeHint(self) -> QSize:
        return QSize(0, MIN_HEIGHT)
