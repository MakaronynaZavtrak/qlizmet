"""Экран выбора режима обучения.

Показывает все режимы карточками: иконка, название и строка пояснения.
Недоступный режим не прячется и не отделывается подсказкой под курсором —
причина написана прямо в карточке (``core.study.modes`` её и формулирует).
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
from qlizmet.ui.icons import set_icon
from qlizmet.ui.theme import GAP, PAD
from qlizmet.ui.widgets.mode_card import ModeCard

NOT_READY_HINT = "появится в следующих версиях"
COLUMNS = 3

#: Иконка на карточку режима. Соответствие живёт в интерфейсе — ядро про
#: рисунки ничего не знает.
MODE_ICONS = {
    StudyMode.FLASHCARDS: "cards",
    StudyMode.LEARN: "repeat",
    StudyMode.WRITE: "pencil",
    StudyMode.TEST: "checklist",
    StudyMode.MATCH: "grid",
    StudyMode.GRAVITY: "falling",
}


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

        back = QPushButton("К набору")
        back.setObjectName("backButton")
        set_icon(back, "arrow-left")
        back.clicked.connect(self.back_requested.emit)

        self._title = QLabel()
        self._title.setObjectName("deckTitle")

        header = QHBoxLayout()
        header.addWidget(back)
        header.addWidget(self._title, stretch=1)

        grid = QGridLayout()
        grid.setSpacing(GAP)
        self._cards: dict[StudyMode, ModeCard] = {}
        for index, mode in enumerate(StudyMode):
            card = ModeCard(mode.title, icon_name=MODE_ICONS[mode])
            card.setObjectName("modeCard")
            card.set_hint(mode.description)
            card.clicked.connect(
                lambda _checked=False, m=mode: self.mode_selected.emit(m.value)
            )
            self._cards[mode] = card
            grid.addWidget(card, index // COLUMNS, index % COLUMNS)

        layout = QVBoxLayout()
        layout.setContentsMargins(PAD, PAD, PAD, PAD)
        layout.setSpacing(GAP)
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
        for mode, card in self._cards.items():
            reason = reasons[mode]
            if mode not in self._implemented:
                card.set_available(False, NOT_READY_HINT)
            elif reason:
                card.set_available(False, reason)
            else:
                card.set_available(True, description=mode.description)

    def enabled_modes(self) -> set[StudyMode]:
        """Режимы, карточки которых сейчас активны (удобно для тестов)."""
        return {mode for mode, card in self._cards.items() if card.isEnabled()}

    def button_for(self, mode: StudyMode) -> ModeCard:
        return self._cards[mode]

    def refresh_icons(self) -> None:
        """Перерисовать иконки карточек после смены темы."""
        for card in self._cards.values():
            card.refresh_icon()
