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
from qlizmet.app.scheduler_service import SchedulerService
from qlizmet.core.study import Direction, SessionScope, StudyMode, mode_availability
from qlizmet.ui.widgets.screen_header import ScreenHeader
from qlizmet.ui.theme import GAP, PAD
from qlizmet.ui.widgets.mode_card import ModeCard

NOT_READY_HINT = "появится в следующих версиях"
NOTHING_TODAY_HINT = "на сегодня всё повторено"
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
        scheduler: SchedulerService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._decks = decks
        self._scheduler = scheduler
        self._implemented = implemented if implemented is not None else set(StudyMode)
        self._deck_id: str | None = None
        self._direction = Direction.FRONT_TO_BACK
        self._scope = SessionScope.ALL
        self._cards_by_scope: dict[SessionScope, list] = {}

        self._header = ScreenHeader(back_text="К набору", title_name="deckTitle")
        self._header.back_requested.connect(self.back_requested.emit)

        self._scope_buttons: dict[SessionScope, QPushButton] = {}
        scope_row = QHBoxLayout()
        scope_row.setSpacing(GAP)
        for scope in SessionScope:
            button = QPushButton(scope.title)
            button.setObjectName(f"scope_{scope.value}")
            button.setCheckable(True)
            button.setChecked(scope is SessionScope.ALL)
            button.clicked.connect(
                lambda _checked=False, s=scope: self.set_scope(s)
            )
            self._scope_buttons[scope] = button
            scope_row.addWidget(button)
        scope_row.addStretch(1)

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
        layout.addWidget(self._header)
        layout.addLayout(scope_row)
        layout.addStretch(1)
        layout.addLayout(grid)
        layout.addStretch(1)
        self.setLayout(layout)

    @property
    def deck_id(self) -> str | None:
        return self._deck_id

    def load(self, deck_id: str, direction: Direction = Direction.FRONT_TO_BACK) -> None:
        self._deck_id = deck_id
        self._direction = direction
        deck = self._decks.get(deck_id)
        self._header.set_title(deck.title)

        today = (
            self._scheduler.cards_for_session(deck_id)
            if self._scheduler is not None
            else []
        )
        self._cards_by_scope = {
            SessionScope.ALL: list(deck.cards),
            SessionScope.DUE_TODAY: today,
        }

        self._scope_buttons[SessionScope.ALL].setText(
            f"{SessionScope.ALL.title} ({len(deck.cards)})"
        )
        self._scope_buttons[SessionScope.DUE_TODAY].setText(
            f"{SessionScope.DUE_TODAY.title} ({len(today)})"
        )
        self._scope_buttons[SessionScope.DUE_TODAY].setEnabled(
            self._scheduler is not None
        )
        self._apply_scope()

    @property
    def scope(self) -> SessionScope:
        return self._scope

    def set_scope(self, scope: SessionScope) -> None:
        """Переключить область занятия и пересчитать доступность режимов."""
        self._scope = scope
        for value, button in self._scope_buttons.items():
            button.setChecked(value is scope)
        self._apply_scope()

    def scoped_cards(self) -> list:
        """Карточки, с которыми пойдёт занятие при текущей области."""
        return list(self._cards_by_scope.get(self._scope, []))

    def _apply_scope(self) -> None:
        cards = self._cards_by_scope.get(self._scope, [])
        nothing_today = self._scope is SessionScope.DUE_TODAY and not cards

        reasons = mode_availability(cards, self._direction)
        for mode, card in self._cards.items():
            reason = reasons[mode]
            if mode not in self._implemented:
                card.set_available(False, NOT_READY_HINT)
            elif nothing_today:
                # общее «нужна хотя бы одна карточка» тут только запутало бы
                card.set_available(False, NOTHING_TODAY_HINT)
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
