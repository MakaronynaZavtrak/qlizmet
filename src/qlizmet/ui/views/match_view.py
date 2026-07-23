"""Экран игры «Подбор пар».

Плитки раскладываются сеткой, игрок соединяет лицо и оборот одной карточки на
время. Логика сопоставления живёт в ``MatchGame`` из ядра, а здесь — сетка,
секундомер и подсветка.

Секундомер устроен так, чтобы игру можно было тестировать: ``QTimer`` лишь
вызывает публичный ``tick()``, а тесты дёргают его напрямую и шагают по времени
вручную, ничего не дожидаясь.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qlizmet.core.markup import face_preview
from qlizmet.core.models import Card
from qlizmet.core.study import MatchGame, MatchOutcome
from qlizmet.ui.theme import GAP, PAD, set_state

TICK_MS = 100
COLUMNS = 4
DEFAULT_PAIRS = 6

STATE_IDLE = ""
STATE_SELECTED = "selected"
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
        self._elapsed_ms = 0
        self._buttons: dict[str, QPushButton] = {}

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self.tick)

        back = QPushButton("← Выйти")
        back.setObjectName("backButton")
        back.clicked.connect(self._leave)

        self._clock = QLabel("0.0 с")
        self._clock.setObjectName("clockLabel")
        self._clock.setAlignment(Qt.AlignmentFlag.AlignRight)

        header = QHBoxLayout()
        header.addWidget(back)
        header.addWidget(self._clock, stretch=1)

        self._grid_host = QWidget()
        self._grid_host.setObjectName("tileGrid")
        self._grid_host.setLayout(QGridLayout())

        self._summary = QLabel()
        self._summary.setObjectName("summaryLabel")
        self._summary.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.setContentsMargins(PAD, PAD, PAD, PAD)
        layout.setSpacing(GAP)
        layout.addLayout(header)
        layout.addWidget(self._grid_host, stretch=1)
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
        self._game = MatchGame(cards, pairs=pairs)
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

        if feedback.outcome is MatchOutcome.MISMATCH:
            # подсветим обе плитки красным и погасим через мгновение
            for wrong_id in feedback.tiles:
                self._style(wrong_id, STATE_WRONG)
            QTimer.singleShot(400, self._clear_highlight)
        elif feedback.outcome is MatchOutcome.MATCH:
            self._rebuild_grid()

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

        for index, tile in enumerate(self._game.tiles):
            button = QPushButton(face_preview(tile.face, 28))
            button.setObjectName(f"tile_{index}")
            button.setMinimumHeight(72)
            button.setProperty("tileId", tile.id)
            button.clicked.connect(
                lambda _checked=False, tid=tile.id: self.select_tile(tid)
            )
            self._buttons[tile.id] = button
            grid.addWidget(button, index // COLUMNS, index % COLUMNS)

    def _style(self, tile_id: str, state: str) -> None:
        button = self._buttons.get(tile_id)
        if button is not None:
            set_state(button, state)

    def _clear_highlight(self) -> None:
        selected = self.selected_tile()
        for tile_id, button in self._buttons.items():
            set_state(button, STATE_SELECTED if tile_id == selected else STATE_IDLE)

    def _update_clock(self) -> None:
        self._clock.setText(f"{self.elapsed_seconds:.1f} с")

    def _refresh(self) -> None:
        finished = self.is_finished
        self._grid_host.setVisible(not finished)
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
