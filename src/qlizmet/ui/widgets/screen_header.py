"""Общая шапка экрана.

Раньше каждый экран собирал свою шапку вручную: кнопка возврата, заголовок,
что-то справа — и каждый чуть по-своему. Один компонент убирает разнобой и
десяток повторов.

Кнопка возврата необязательна: на первом экране возвращаться некуда.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from qlizmet.ui.icons import set_icon
from qlizmet.ui.theme import GAP


class ScreenHeader(QWidget):
    """Шапка: возврат слева, заголовок по центру-слева, действия справа."""

    back_requested = Signal()

    def __init__(
        self,
        title: str = "",
        *,
        back_text: str | None = "Назад",
        title_name: str = "screenTitle",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("screenHeader")

        self._layout = QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(GAP)

        self._back: QPushButton | None = None
        if back_text is not None:
            button = QPushButton(back_text)
            button.setObjectName("backButton")
            set_icon(button, "arrow-left")
            button.clicked.connect(self.back_requested.emit)
            self._back = button
            self._layout.addWidget(button)

        self._title = QLabel(title)
        self._title.setObjectName(title_name)
        self._title.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._layout.addWidget(self._title, stretch=1)

        self.setLayout(self._layout)

    @property
    def back_button(self) -> QPushButton | None:
        return self._back

    def set_title(self, text: str) -> None:
        self._title.setText(text)

    def title_text(self) -> str:
        return self._title.text()

    def add_action(self, widget: QWidget) -> QWidget:
        """Добавить виджет справа (кнопку действия, счётчик, секундомер)."""
        self._layout.addWidget(widget)
        return widget
