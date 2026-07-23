"""Экран игры «Гравитация».

Термин падает сверху вниз, игрок успевает набрать ответ. Верно — очки и рост
уровня; не успел или ошибся — минус жизнь. Счёт, жизни и уровни считает
``GravityGame`` из ядра, здесь — падение и ввод.

Как и в «Подборе пар», падение отделено от таймера: ``QTimer`` лишь вызывает
публичный ``tick()``, поэтому тесты шагают по времени вручную и проходят мгновенно.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qlizmet.core.models import Card
from qlizmet.core.study import Direction, GravityGame
from qlizmet.ui.theme import set_state
from qlizmet.ui.widgets.face_view import FaceView

TICK_MS = 250
#: Сколько тиков падает термин на первом уровне и предел ускорения.
STEPS_AT_LEVEL_1 = 16
MIN_STEPS = 5


def steps_for_level(level: int) -> int:
    """Сколько тиков падает термин на данном уровне (чем выше, тем быстрее)."""
    return max(MIN_STEPS, STEPS_AT_LEVEL_1 - 2 * (level - 1))


class GravityView(QWidget):
    """Падающие термины с вводом ответа."""

    back_requested = Signal()

    def __init__(
        self,
        *,
        media_root: Path | str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._game: GravityGame | None = None
        self._step = 0

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self.tick)

        back = QPushButton("← Выйти")
        back.setObjectName("backButton")
        back.clicked.connect(self._leave)

        self._status = QLabel()
        self._status.setObjectName("statusLabel")
        self._status.setAlignment(Qt.AlignmentFlag.AlignRight)

        header = QHBoxLayout()
        header.addWidget(back)
        header.addWidget(self._status, stretch=1)

        # область падения: термин зажат между двумя распорками,
        # соотношение которых и создаёт эффект движения вниз
        self._term = FaceView(media_root=media_root)
        self._term.setObjectName("termFace")
        top_spacer = QWidget()
        bottom_spacer = QWidget()

        fall_layout = QVBoxLayout()
        fall_layout.setContentsMargins(0, 0, 0, 0)
        fall_layout.addWidget(top_spacer, 0)
        fall_layout.addWidget(self._term, 0)
        fall_layout.addWidget(bottom_spacer, 1)
        self._fall_area = QWidget()
        self._fall_area.setObjectName("fallArea")
        self._fall_area.setLayout(fall_layout)

        self._answer_edit = QLineEdit()
        self._answer_edit.setObjectName("answerEdit")
        self._answer_edit.setPlaceholderText("Успей написать ответ")
        self._answer_edit.returnPressed.connect(self.submit)

        submit_button = QPushButton("Ответить")
        submit_button.setObjectName("submitButton")
        submit_button.clicked.connect(self.submit)
        self._submit_button = submit_button

        self._flash = QLabel()
        self._flash.setObjectName("flashLabel")
        self._flash.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._summary = QLabel()
        self._summary.setObjectName("summaryLabel")
        self._summary.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addWidget(self._fall_area, stretch=1)
        layout.addWidget(self._flash)
        layout.addWidget(self._answer_edit)
        layout.addWidget(submit_button)
        layout.addWidget(self._summary)
        self.setLayout(layout)

    # --- управление игрой ---

    def start(
        self,
        cards: Sequence[Card],
        *,
        direction: Direction = Direction.FRONT_TO_BACK,
        lives: int = 3,
        autostart: bool = True,
    ) -> None:
        self._game = GravityGame(cards, direction=direction, lives=lives)
        self._step = 0
        self._answer_edit.clear()
        self._flash.clear()
        self._refresh()
        if autostart and not self.is_over:
            self._timer.start()

    @property
    def is_over(self) -> bool:
        return self._game is None or self._game.is_over

    @property
    def score(self) -> int:
        return 0 if self._game is None else self._game.score

    @property
    def lives(self) -> int:
        return 0 if self._game is None else self._game.lives

    @property
    def level(self) -> int:
        return 1 if self._game is None else self._game.level

    @property
    def fall_step(self) -> int:
        """Сколько тиков термин уже падает (для тестов и отладки)."""
        return self._step

    def tick(self) -> None:
        """Один шаг падения. Достигнув дна, термин засчитывается пропущенным."""
        if self.is_over:
            return
        self._step += 1
        if self._step >= steps_for_level(self.level):
            self._game.miss()
            self._step = 0
            self._flash.setText("Не успел!")
            set_state(self._flash, "bad")
        self._refresh()

    def submit(self) -> None:
        if self.is_over:
            return
        text = self._answer_edit.text()
        feedback = self._game.answer(text)
        self._step = 0
        self._answer_edit.clear()
        self._flash.setText(
            "Верно!" if feedback.is_correct
            else f"Неверно: {feedback.correct_answer.plain_text}"
        )
        set_state(self._flash, "ok" if feedback.is_correct else "bad")
        self._refresh()

    def status_text(self) -> str:
        return self._status.text()

    def summary_text(self) -> str:
        return self._summary.text()

    def flash_text(self) -> str:
        return self._flash.text()

    # --- внутреннее ---

    def _leave(self) -> None:
        self._timer.stop()
        self.back_requested.emit()

    def _refresh(self) -> None:
        over = self.is_over

        self._fall_area.setVisible(not over)
        self._answer_edit.setVisible(not over)
        self._submit_button.setVisible(not over)
        self._summary.setVisible(over)

        if over:
            self._timer.stop()
            if self._game is not None:
                summary = self._game.summary()
                self._summary.setText(
                    f"Игра окончена! Очки: {summary.score}, "
                    f"верно: {summary.correct}, промахов: {summary.missed}"
                )
            self._status.setText("")
            return

        hearts = "♥" * self.lives
        self._status.setText(
            f"Очки: {self.score}   Уровень: {self.level}   Жизни: {hearts}"
        )

        prompt = self._game.current()
        if prompt is not None:
            self._term.set_face(prompt.prompt)
            self._answer_edit.setFocus()

        # двигаем термин вниз, меняя соотношение распорок
        total = steps_for_level(self.level)
        layout = self._fall_area.layout()
        layout.setStretch(0, self._step)
        layout.setStretch(2, max(total - self._step, 0))
