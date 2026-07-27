"""Экран игры «Подбор пар».

Плитки раскладываются сеткой, игрок соединяет лицо и оборот одной карточки на
время. Логика сопоставления живёт в ``MatchGame`` из ядра, а здесь — сетка,
секундомер и подсветка.

Плитка показывает содержимое целиком: формулу — картинкой, текст — с переносом
по словам, и растёт в высоту под длинный текст. Сетка обёрнута в прокрутку, так
что при большом объёме плитки можно пролистать целиком.

Секундомер устроен так, чтобы игру можно было тестировать: ``QTimer`` лишь
вызывает публичный ``tick()``, а тесты дёргают его напрямую и шагают по времени
вручную, ничего не дожидаясь.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from qlizmet.core.markup import face_preview
from qlizmet.core.models import Card
from qlizmet.core.study import MatchGame, MatchOutcome, MatchRotation
from qlizmet.ui.formula import formula_pixmap, single_formula
from qlizmet.ui.widgets.choice_button import ChoiceButton
from qlizmet.ui.widgets.screen_header import ScreenHeader
from qlizmet.ui.theme import GAP, PAD, current_palette, set_state

TICK_MS = 100
COLUMNS = 4
DEFAULT_PAIRS = 6

#: Сколько держится подсветка совпадения/промаха, прежде чем погаснуть.
FLASH_MS = 320
#: Максимальная высота формулы-картинки на плитке.
TILE_FORMULA_HEIGHT = 40

STATE_IDLE = ""
STATE_SELECTED = "selected"
STATE_MATCH = "match"
STATE_WRONG = "wrong"


class MatchView(QWidget):
    """Сопоставление пар на время."""

    back_requested = Signal()

    def __init__(
        self,
        *,
        media_root: Path | str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._media_root = media_root
        self._game: MatchGame | None = None
        self._rotation: MatchRotation | None = None
        self._rotation_deck: tuple[str, ...] = ()
        self._elapsed_ms = 0
        self._buttons: dict[str, ChoiceButton] = {}

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self.tick)

        header = ScreenHeader(back_text="Выйти")
        header.back_requested.connect(self._leave)

        self._clock = QLabel("0.0 с")
        self._clock.setObjectName("clockLabel")
        self._clock.setAlignment(Qt.AlignmentFlag.AlignRight)

        header.add_action(self._clock)

        self._grid_host = QWidget()
        self._grid_host.setObjectName("tileGrid")
        self._grid_host.setLayout(QGridLayout())

        # сетка прокручивается: длинные плитки растут в высоту, а всё поле можно
        # пролистать вверх-вниз, если оно не влезает на экран
        self._scroll = QScrollArea()
        self._scroll.setObjectName("matchScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setWidget(self._grid_host)

        self._summary = QLabel()
        self._summary.setObjectName("summaryLabel")
        self._summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._summary.setWordWrap(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(PAD, PAD, PAD, PAD)
        layout.setSpacing(GAP)
        layout.addWidget(header)
        layout.addWidget(self._scroll, stretch=1)
        layout.addWidget(self._summary)
        self.setLayout(layout)

    # --- управление игрой ---

    def start(
        self,
        cards: Sequence[Card],
        *,
        pairs: int = DEFAULT_PAIRS,
        autostart: bool = True,
    ) -> None:
        # ротация помнит, какие карточки уже были: при каждом заходе — новая
        # пачка, с проходом по всему набору. Смена набора сбрасывает ротацию.
        deck = list(cards)
        deck_ids = tuple(card.id for card in deck)
        if self._rotation is None or self._rotation_deck != deck_ids:
            self._rotation = MatchRotation(deck)
            self._rotation_deck = deck_ids

        batch = self._rotation.next_batch(pairs)
        self._game = MatchGame(batch)
        self._elapsed_ms = 0
        self._rebuild_grid()
        self._refresh()
        if autostart:
            self._timer.start()

    @property
    def is_finished(self) -> bool:
        return self._game is None or self._game.is_finished

    @property
    def elapsed_seconds(self) -> float:
        return self._elapsed_ms / 1000

    def tick(self) -> None:
        """Один шаг секундомера. Вызывается таймером, а в тестах — напрямую."""
        if self.is_finished:
            return
        self._elapsed_ms += TICK_MS
        self._update_clock()

    def tile_ids(self) -> list[str]:
        """Плитки, оставшиеся на поле (в порядке раскладки)."""
        return [] if self._game is None else [tile.id for tile in self._game.tiles]

    def selected_tile(self) -> str | None:
        return None if self._game is None else self._game.selected

    def select_tile(self, tile_id: str) -> MatchOutcome | None:
        if self._game is None or self._game.is_finished:
            return None
        feedback = self._game.select(tile_id)

        if feedback.outcome is MatchOutcome.MATCH:
            if self.is_finished:
                # последняя пара — сразу показываем итог, вспышка уже ни к чему
                self._refresh()
            else:
                # зелёная вспышка на совпавшей паре, затем убираем её с поля
                for matched_id in feedback.tiles:
                    self._style(matched_id, STATE_MATCH)
                    button = self._buttons.get(matched_id)
                    if button is not None:
                        button.setEnabled(False)  # плитка уже уходит, клики не нужны
                self._update_clock()
                QTimer.singleShot(FLASH_MS, self._settle_after_match)
        elif feedback.outcome is MatchOutcome.MISMATCH:
            # красная вспышка на обеих плитках, затем гасим
            for wrong_id in feedback.tiles:
                self._style(wrong_id, STATE_WRONG)
            self._update_clock()
            QTimer.singleShot(FLASH_MS, self._clear_highlight)
        else:
            self._refresh()
        return feedback.outcome

    def summary_text(self) -> str:
        return self._summary.text()

    def clock_text(self) -> str:
        return self._clock.text()

    # --- внутреннее ---

    def _leave(self) -> None:
        self._timer.stop()
        self.back_requested.emit()

    def _rebuild_grid(self) -> None:
        grid = self._grid_host.layout()
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._buttons.clear()

        if self._game is None:
            return

        # колонки равной ширины
        for column in range(COLUMNS):
            grid.setColumnStretch(column, 1)

        for index, tile in enumerate(self._game.tiles):
            button = ChoiceButton()
            button.setObjectName(f"tile_{index}")
            button.setMinimumHeight(72)
            button.setProperty("tileId", tile.id)
            latex = single_formula(tile.face)
            pixmap = (
                formula_pixmap(latex, current_palette().text, TILE_FORMULA_HEIGHT)
                if latex is not None
                else None
            )
            if pixmap is not None:
                # плитку-формулу показываем самой формулой, а не сырым LaTeX
                button.set_formula(pixmap)
            else:
                # полный текст с переносом — плитка растёт в высоту
                button.set_text(tile.face.plain_text or face_preview(tile.face))
            button.clicked.connect(
                lambda _checked=False, tid=tile.id: self.select_tile(tid)
            )
            self._buttons[tile.id] = button
            grid.addWidget(button, index // COLUMNS, index % COLUMNS)

    def _style(self, tile_id: str, state: str) -> None:
        button = self._buttons.get(tile_id)
        if button is not None:
            set_state(button, state)

    def _settle_after_match(self) -> None:
        """Убрать совпавшую пару с поля после зелёной вспышки."""
        self._rebuild_grid()
        self._refresh()

    def _clear_highlight(self) -> None:
        selected = self.selected_tile()
        for tile_id, button in self._buttons.items():
            set_state(button, STATE_SELECTED if tile_id == selected else STATE_IDLE)

    def _update_clock(self) -> None:
        self._clock.setText(f"{self.elapsed_seconds:.1f} с")

    def _refresh(self) -> None:
        finished = self.is_finished
        self._scroll.setVisible(not finished)
        self._summary.setVisible(finished)
        self._update_clock()
        self._clear_highlight()

        if finished:
            self._timer.stop()
            if self._game is not None:
                summary = self._game.summary()
                self._summary.setText(
                    f"Готово за {self.elapsed_seconds:.1f} с! "
                    f"Пар: {summary.matched}, промахов: {summary.mismatches}"
                )
