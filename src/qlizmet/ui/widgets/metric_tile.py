"""Плитка с показателем: крупное число и подпись под ним.

Нужна там, где числа должны читаться с одного взгляда — в анкете вида
«подпись: значение» одинаковым мелким шрифтом они теряются.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

TILE_MIN_WIDTH = 140
TILE_MIN_HEIGHT = 84


class MetricTile(QFrame):
    """Показатель: значение крупно, подпись мелко."""

    def __init__(
        self,
        caption: str,
        *,
        value_name: str,
        accent: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("metricTileAccent" if accent else "metricTile")
        self.setMinimumSize(TILE_MIN_WIDTH, TILE_MIN_HEIGHT)

        self._value = QLabel("—")
        self._value.setObjectName(value_name)
        self._value.setProperty("class", "metricValue")

        self._caption = QLabel(caption)
        self._caption.setObjectName("metricCaption")
        self._caption.setWordWrap(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._value)
        layout.addWidget(self._caption)
        self.setLayout(layout)

    def set_value(self, text: str) -> None:
        self._value.setText(text)

    def value_text(self) -> str:
        return self._value.text()

    def caption_text(self) -> str:
        return self._caption.text()
