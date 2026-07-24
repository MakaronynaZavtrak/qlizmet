"""Экран статистики по набору.

Показывает состояние набора плитками — крупные числа читаются с одного взгляда —
и составной полосой, где видно соотношение новых, изучаемых и закреплённых
карточек.
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

from qlizmet.app.stats_service import StatsService
from qlizmet.core.stats import MATURE_INTERVAL_DAYS, DeckStats
from qlizmet.ui.widgets.screen_header import ScreenHeader
from qlizmet.ui.theme import GAP, PAD, current_palette
from qlizmet.ui.widgets.metric_tile import MetricTile
from qlizmet.ui.widgets.segmented_bar import Segment, SegmentedBar

COLUMNS = 3


class StatsView(QWidget):
    """Сводка прогресса по одному набору."""

    back_requested = Signal()

    def __init__(
        self,
        stats: StatsService | None = None,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._stats = stats
        self._deck_id: str | None = None

        header = ScreenHeader("Статистика", back_text="К набору")
        header.back_requested.connect(self.back_requested.emit)

        self._bar = SegmentedBar()
        self._legend = QLabel()
        self._legend.setObjectName("legendLabel")
        self._legend.setWordWrap(True)

        self._tiles = {
            "total": MetricTile("Всего карточек", value_name="totalValue"),
            "new": MetricTile("Новых", value_name="newValue"),
            "learning": MetricTile("В работе", value_name="learningValue"),
            "mature": MetricTile(
                f"Закреплено (интервал ≥ {MATURE_INTERVAL_DAYS} дн.)",
                value_name="matureValue",
            ),
            "due": MetricTile("Пора повторить", value_name="dueValue", accent=True),
            "accuracy": MetricTile("Верных ответов", value_name="accuracyValue"),
        }

        grid = QGridLayout()
        grid.setSpacing(GAP)
        for index, tile in enumerate(self._tiles.values()):
            grid.addWidget(tile, index // COLUMNS, index % COLUMNS)

        self._hint = QLabel()
        self._hint.setObjectName("hintLabel")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setWordWrap(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(PAD, PAD, PAD, PAD)
        layout.setSpacing(GAP)
        layout.addWidget(header)
        layout.addStretch(1)
        layout.addWidget(self._bar)
        layout.addWidget(self._legend)
        layout.addLayout(grid)
        layout.addWidget(self._hint)
        layout.addStretch(1)
        self.setLayout(layout)

    @property
    def deck_id(self) -> str | None:
        return self._deck_id

    def load(self, deck_id: str) -> None:
        self._deck_id = deck_id
        self.refresh()

    def refresh(self) -> None:
        if self._deck_id is None:
            return
        if self._stats is None:
            # сервис не подключён (бывает в тестах отдельных экранов)
            self._hint.setText("Статистика недоступна.")
            return
        self._render(self._stats.deck_stats(self._deck_id))

    def hint_text(self) -> str:
        return self._hint.text()

    def legend_text(self) -> str:
        return self._legend.text()

    def tile(self, name: str) -> MetricTile:
        return self._tiles[name]

    # --- внутреннее ---

    def _render(self, stats: DeckStats) -> None:
        palette = current_palette()

        self._bar.set_segments(
            [
                Segment(stats.mature, palette.accent, "закреплено"),
                Segment(stats.learning, palette.accent_hover, "в работе"),
                Segment(stats.new, palette.text_muted, "новых"),
            ],
            empty_color=palette.surface_alt,
        )
        self._legend.setText(
            f"закреплено {stats.mature} · в работе {stats.learning} · новых {stats.new}"
        )

        self._tiles["total"].set_value(str(stats.total))
        self._tiles["new"].set_value(str(stats.new))
        self._tiles["learning"].set_value(str(stats.learning))
        self._tiles["mature"].set_value(str(stats.mature))
        self._tiles["due"].set_value(str(stats.due))
        self._tiles["accuracy"].set_value(
            "—" if stats.reviews == 0 else f"{round(stats.accuracy * 100)}%"
        )

        if stats.total == 0:
            self._hint.setText("В наборе ещё нет карточек.")
        elif stats.reviews == 0:
            self._hint.setText("Набор ещё не изучался — самое время начать.")
        elif stats.due:
            self._hint.setText(f"Сегодня стоит повторить карточек: {stats.due}.")
        else:
            self._hint.setText("На сегодня всё повторено — можно отдыхать.")
