"""Экран режима «Карточки».

Показывает вопрос, по нажатию переворачивает карточку и принимает самооценку
«знаю / не знаю». Вся логика прохода живёт в ``FlashcardSession`` из ядра —
экран только рисует её состояние.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qlizmet.core.models import Card
from qlizmet.core.study import Direction, FlashcardSession
from qlizmet.ui.theme import GAP, PAD
from qlizmet.ui.widgets.card_surface import CardSurface
from qlizmet.ui.widgets.face_view import FaceView


class FlashcardsView(QWidget):
    """Проход по колоде с переворотом карточки."""

    back_requested = Signal()

    def __init__(
        self,
        *,
        media_root: Path | str | None = None,
        animated: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._session: FlashcardSession | None = None
        self._answer_shown = False

        back = QPushButton("← Выйти")
        back.setObjectName("backButton")
        back.clicked.connect(self.back_requested.emit)

        self._progress = QLabel()
        self._progress.setObjectName("progressLabel")
        self._progress.setAlignment(Qt.AlignmentFlag.AlignRight)

        header = QHBoxLayout()
        header.addWidget(back)
        header.addWidget(self._progress, stretch=1)

        self._face = FaceView(media_root=media_root)
        self._face.setObjectName("cardFace")
        self._card = CardSurface(self._face, animated=animated)

        flip_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        flip_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        flip_shortcut.activated.connect(self.flip)

        self._side_label = QLabel()
        self._side_label.setObjectName("sideLabel")
        self._side_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._summary = QLabel()
        self._summary.setObjectName("summaryLabel")
        self._summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._summary.setVisible(False)

        self._flip_button = QPushButton("Показать ответ")
        self._flip_button.setObjectName("flipButton")
        self._flip_button.clicked.connect(self.flip)

        self._dont_know_button = QPushButton("Не знаю")
        self._dont_know_button.setObjectName("dontKnowButton")
        self._dont_know_button.clicked.connect(lambda: self.mark(False))

        self._know_button = QPushButton("Знаю")
        self._know_button.setObjectName("knowButton")
        self._know_button.clicked.connect(lambda: self.mark(True))

        buttons = QHBoxLayout()
        buttons.addWidget(self._dont_know_button)
        buttons.addWidget(self._flip_button)
        buttons.addWidget(self._know_button)

        layout = QVBoxLayout()
        layout.setContentsMargins(PAD, PAD, PAD, PAD)
        layout.setSpacing(GAP)
        layout.addLayout(header)
        layout.addStretch(1)
        layout.addWidget(self._side_label)
        layout.addWidget(self._card, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._summary)
        layout.addStretch(1)
        layout.addLayout(buttons)
        self.setLayout(layout)

    # --- управление сессией ---

    def start(
        self,
        cards: Sequence[Card],
        *,
        direction: Direction = Direction.FRONT_TO_BACK,
        shuffle: bool = True,
    ) -> None:
        self._session = FlashcardSession(cards, direction=direction, shuffle=shuffle)
        self._answer_shown = False
        self._refresh()

    @property
    def is_finished(self) -> bool:
        return self._session is None or self._session.is_finished

    @property
    def answer_shown(self) -> bool:
        return self._answer_shown

    def flip(self) -> None:
        """Перевернуть карточку. Состояние меняется сразу, анимация — украшение."""
        if self.is_finished:
            return
        self._answer_shown = not self._answer_shown
        self._card.flip(self._refresh)

    def mark(self, known: bool) -> None:
        if self.is_finished:
            return
        self._session.mark(known)
        self._answer_shown = False
        self._card.stop_animation()
        self._refresh()

    def progress_text(self) -> str:
        return self._progress.text()

    def summary_text(self) -> str:
        return self._summary.text()

    # --- отрисовка ---

    def _refresh(self) -> None:
        prompt = self._session.current() if self._session else None
        finished = prompt is None

        self._card.setVisible(not finished)
        self._side_label.setVisible(not finished)
        self._summary.setVisible(finished)
        for button in (self._flip_button, self._know_button, self._dont_know_button):
            button.setVisible(not finished)

        if finished:
            self._progress.setText("")
            if self._session is not None:
                summary = self._session.summary()
                self._summary.setText(
                    f"Готово! Знаю: {summary.known} из {summary.total}"
                )
            return

        self._progress.setText(f"{prompt.index + 1} / {prompt.total}")
        self._side_label.setText("Ответ" if self._answer_shown else "Вопрос")
        self._face.set_face(prompt.answer if self._answer_shown else prompt.prompt)
        self._flip_button.setText(
            "Показать вопрос" if self._answer_shown else "Показать ответ"
        )
