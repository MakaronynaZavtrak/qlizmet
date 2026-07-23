"""Карточка режима обучения.

Снаружи это обычная кнопка — со всеми её повадками: нажатие, наведение, фокус,
пробел и Enter с клавиатуры, отключённое состояние. Внутри — раскладка с
иконкой, названием и пояснением, поэтому выглядит она карточкой, а не серым
прямоугольником.

Наследование от ``QPushButton`` выбрано намеренно: рисовать «кликабельную рамку»
с нуля означало бы вручную повторять обработку клавиатуры и фокуса, то есть
сломать доступность там, где Qt всё делает сам.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from qlizmet.ui.icons import icon
from qlizmet.ui.theme import current_palette

CARD_MIN_WIDTH = 190
CARD_MIN_HEIGHT = 104
ICON_SIZE = 22


class ModeCard(QPushButton):
    """Кнопка режима: иконка, название и строка пояснения."""

    def __init__(
        self,
        title: str,
        *,
        icon_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon_name = icon_name
        self.setMinimumSize(CARD_MIN_WIDTH, CARD_MIN_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._icon = QLabel()
        self._icon.setObjectName("modeCardIcon")

        self._title = QLabel(title)
        self._title.setObjectName("modeCardTitle")

        self._hint = QLabel()
        self._hint.setObjectName("modeCardHint")
        self._hint.setWordWrap(True)

        # подписи не должны перехватывать клики — иначе кнопка перестанет нажиматься
        for label in (self._icon, self._title, self._hint):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        layout.addWidget(self._icon)
        layout.addWidget(self._title)
        layout.addWidget(self._hint)
        layout.addStretch(1)
        self.setLayout(layout)

        self.refresh_icon()

    @property
    def icon_name(self) -> str:
        return self._icon_name

    def title_text(self) -> str:
        return self._title.text()

    def hint_text(self) -> str:
        return self._hint.text()

    def set_hint(self, text: str) -> None:
        self._hint.setText(text)

    def set_available(self, available: bool, reason: str = "", description: str = "") -> None:
        """Задать доступность режима: недоступный объясняет причину прямо в карточке."""
        self.setEnabled(available)
        self.set_hint(description if available else reason)
        self.setToolTip("" if available else reason)
        self.refresh_icon()

    def refresh_icon(self) -> None:
        """Перерисовать иконку в цветах текущей темы и текущего состояния."""
        palette = current_palette()
        color = palette.accent if self.isEnabled() else palette.text_muted
        self._icon.setPixmap(icon(self._icon_name, color=color, size=ICON_SIZE).pixmap(ICON_SIZE, ICON_SIZE))
