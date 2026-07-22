"""Экран выбора режима обучения.

Показывает все режимы, но включает только те, что доступны для этого набора
(см. ``core.study.modes``) и уже реализованы. Недоступная кнопка гаснет и
объясняет причину подсказкой — это честнее, чем прятать её совсем.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qlizmet.app.deck_service import DeckService
from qlizmet.core.study import Direction, StudyMode, mode_availability

NOT_READY_HINT = "появится в следующих версиях"


class ModeSelectView(QWidget):
    """Выбор режима для конкретного набора."""

    mode_selected = Signal(str)
    back_requested = Signal()

    def __init__(
        self,
        decks: DeckService,
        implemented: set[StudyMode] | None = None,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._decks = decks
        self._implemented = implemented if implemented is not None else set(StudyMode)
        self._deck_id: str | None = None

        back = QPushButton("← К набору")
        back.setObjectName("backButton")
        back.clicked.connect(self.back_requested.emit)

        self._title = QLabel()
        self._title.setObjectName("deckTitle")
        self._title.setStyleSheet("font-size: 20px; font-weight: 600;")

        header = QHBoxLayout()
        header.addWidget(back)
        header.addWidget(self._title, stretch=1)

        grid = QGridLayout()
        self._buttons: dict[StudyMode, QPushButton] = {}
        for index, mode in enumerate(StudyMode):
            button = QPushButton(mode.title)
            button.setObjectName(f"mode_{mode.value}")
            button.setMinimumHeight(64)
            button.clicked.connect(
                lambda _checked=False, m=mode: self.mode_selected.emit(m.value)
            )
            self._buttons[mode] = button
            grid.addWidget(button, index // 2, index % 2)

        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addStretch(1)
        layout.addLayout(grid)
        layout.addStretch(1)
        self.setLayout(layout)

    @property
    def deck_id(self) -> str | None:
        return self._deck_id

    def load(self, deck_id: str, direction: Direction = Direction.FRONT_TO_BACK) -> None:
        self._deck_id = deck_id
        deck = self._decks.get(deck_id)
        self._title.setText(deck.title)

        reasons = mode_availability(deck.cards, direction)
        for mode, button in self._buttons.items():
            reason = reasons[mode]
            ready = mode in self._implemented
            button.setEnabled(reason is None and ready)
            if not ready:
                button.setToolTip(NOT_READY_HINT)
            elif reason:
                button.setToolTip(reason)
            else:
                button.setToolTip("")

    def enabled_modes(self) -> set[StudyMode]:
        """Режимы, кнопки которых сейчас активны (удобно для тестов)."""
        return {mode for mode, button in self._buttons.items() if button.isEnabled()}

    def button_for(self, mode: StudyMode) -> QPushButton:
        return self._buttons[mode]