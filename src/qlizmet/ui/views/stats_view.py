"""Экран статистики по набору.

Показывает, сколько карточек новых, в работе и закреплённых, сколько пора
повторить сегодня и какова доля верных ответов за всю историю.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qlizmet.app.stats_service import StatsService
from qlizmet.core.stats import MATURE_INTERVAL_DAYS, DeckStats


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

        back = QPushButton("← К набору")
        back.setObjectName("backButton")
        back.clicked.connect(self.back_requested.emit)

        title = QLabel("Статистика")
        title.setObjectName("screenTitle")

        header = QHBoxLayout()
        header.addWidget(back)
        header.addWidget(title, stretch=1)

        self._bar = QProgressBar()
        self._bar.setObjectName("masteryBar")
        self._bar.setRange(0, 100)
        self._bar.setFormat("закреплено %p%")

        self._total = QLabel()
        self._total.setObjectName("totalValue")
        self._new = QLabel()
        self._new.setObjectName("newValue")
        self._learning = QLabel()
        self._learning.setObjectName("learningValue")
        self._mature = QLabel()
        self._mature.setObjectName("matureValue")
        self._due = QLabel()
        self._due.setObjectName("dueValue")
        self._accuracy = QLabel()
        self._accuracy.setObjectName("accuracyValue")

        form = QFormLayout()
        form.addRow("Всего карточек:", self._total)
        form.addRow("Новых:", self._new)
        form.addRow("В работе:", self._learning)
        form.addRow(f"Закреплено (интервал ≥ {MATURE_INTERVAL_DAYS} дн.):", self._mature)
        form.addRow("Пора повторить:", self._due)
        form.addRow("Верных ответов:", self._accuracy)

        self._hint = QLabel()
        self._hint.setObjectName("hintLabel")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addStretch(1)
        layout.addWidget(self._bar)
        layout.addLayout(form)
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

    # --- внутреннее ---

    def _render(self, stats: DeckStats) -> None:
        self._bar.setValue(round(stats.mastery * 100))
        self._total.setText(str(stats.total))
        self._new.setText(str(stats.new))
        self._learning.setText(str(stats.learning))
        self._mature.setText(str(stats.mature))
        self._due.setText(str(stats.due))
        self._accuracy.setText(
            "пока нет ответов"
            if stats.reviews == 0
            else f"{round(stats.accuracy * 100)}% ({stats.correct} из {stats.reviews})"
        )

        if stats.total == 0:
            self._hint.setText("В наборе ещё нет карточек.")
        elif stats.reviews == 0:
            self._hint.setText("Набор ещё не изучался — самое время начать.")
        elif stats.due:
            self._hint.setText(f"Сегодня стоит повторить карточек: {stats.due}.")
        else:
            self._hint.setText("На сегодня всё повторено — можно отдыхать.")
