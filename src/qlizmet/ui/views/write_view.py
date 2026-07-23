"""Экран режима «Письмо».

Показывает вопрос, принимает набранный ответ и разбирает его грейдером. Если
ответ отклонён, доступна кнопка «Я был прав» — как в quizlet.

Результат каждой карточки записывается через ``StudyService`` (SM-2 + история),
причём **после** возможного переопределения: иначе в истории остался бы неверный
вердикт, который пользователь только что оспорил.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qlizmet.app.study_service import StudyService, grade_from_verdict
from qlizmet.core.models import Card
from qlizmet.core.study import Direction, WriteFeedback, WriteSession
from qlizmet.ui.theme import set_state
from qlizmet.ui.widgets.face_view import FaceView

VERDICT_TEXT = {
    "exact": "Верно!",
    "typo": "Почти — засчитано с опечаткой",
    "incorrect": "Неверно",
}


class WriteView(QWidget):
    """Ввод ответа с проверкой и записью прогресса."""

    back_requested = Signal()

    def __init__(
        self,
        study: StudyService | None = None,
        *,
        media_root: Path | str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._study = study
        self._session: WriteSession | None = None
        self._pending: tuple[str, WriteFeedback, str] | None = None

        back = QPushButton("← Выйти")
        back.setObjectName("backButton")
        back.clicked.connect(self.back_requested.emit)

        self._progress = QLabel()
        self._progress.setObjectName("progressLabel")
        self._progress.setAlignment(Qt.AlignmentFlag.AlignRight)

        header = QHBoxLayout()
        header.addWidget(back)
        header.addWidget(self._progress, stretch=1)

        self._prompt = FaceView(media_root=media_root)
        self._prompt.setObjectName("promptFace")

        self._answer_edit = QLineEdit()
        self._answer_edit.setObjectName("answerEdit")
        self._answer_edit.setPlaceholderText("Ваш ответ")
        self._answer_edit.returnPressed.connect(self.submit)

        self._verdict = QLabel()
        self._verdict.setObjectName("verdictLabel")
        self._verdict.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._correct_answer = FaceView(media_root=media_root)
        self._correct_answer.setObjectName("correctAnswerFace")

        self._summary = QLabel()
        self._summary.setObjectName("summaryLabel")
        self._summary.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._submit_button = QPushButton("Ответить")
        self._submit_button.setObjectName("submitButton")
        self._submit_button.clicked.connect(self.submit)

        self._override_button = QPushButton("Я был прав")
        self._override_button.setObjectName("overrideButton")
        self._override_button.clicked.connect(self.override)

        self._next_button = QPushButton("Дальше")
        self._next_button.setObjectName("nextButton")
        self._next_button.clicked.connect(self.next_card)

        buttons = QHBoxLayout()
        buttons.addWidget(self._submit_button)
        buttons.addWidget(self._override_button)
        buttons.addWidget(self._next_button)

        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addStretch(1)
        layout.addWidget(self._prompt)
        layout.addWidget(self._answer_edit)
        layout.addWidget(self._verdict)
        layout.addWidget(self._correct_answer)
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
        self._session = WriteSession(cards, direction=direction, shuffle=shuffle)
        self._pending = None
        self._answer_edit.clear()
        self._refresh()

    @property
    def is_finished(self) -> bool:
        return self._session is None or (
            self._session.is_finished and self._pending is None
        )

    @property
    def awaiting_next(self) -> bool:
        """Ответ разобран, ждём перехода к следующей карточке."""
        return self._pending is not None

    def submit(self) -> None:
        if self._session is None or self._session.is_finished or self._pending:
            return
        prompt = self._session.current()
        text = self._answer_edit.text()
        feedback = self._session.submit(text)
        self._pending = (prompt.card_id, feedback, text)
        self._refresh()

    def override(self) -> None:
        """«Я был прав» — засчитать текущий ответ верным."""
        if self._session is None or self._pending is None:
            return
        card_id, feedback, text = self._pending
        if feedback.is_accepted:
            return
        self._pending = (card_id, self._session.override_last(), text)
        self._refresh()

    def next_card(self) -> None:
        if self._pending is None:
            return
        card_id, feedback, text = self._pending
        self._record(card_id, feedback, text)
        self._pending = None
        self._answer_edit.clear()
        self._refresh()

    def verdict_text(self) -> str:
        return self._verdict.text()

    def summary_text(self) -> str:
        return self._summary.text()

    def progress_text(self) -> str:
        return self._progress.text()

    # --- внутреннее ---

    def _record(self, card_id: str, feedback: WriteFeedback, text: str) -> None:
        if self._study is None:
            return
        self._study.record(
            card_id,
            grade_from_verdict(feedback.result.verdict),
            mode="write",
            user_answer=text,
        )

    def _refresh(self) -> None:
        finished = self.is_finished
        showing_feedback = self._pending is not None

        self._summary.setVisible(finished)
        self._prompt.setVisible(not finished)
        self._answer_edit.setVisible(not finished)
        self._answer_edit.setEnabled(not showing_feedback)
        self._verdict.setVisible(showing_feedback)
        self._correct_answer.setVisible(showing_feedback)
        self._submit_button.setVisible(not finished and not showing_feedback)
        self._next_button.setVisible(showing_feedback)

        if finished:
            self._progress.setText("")
            self._override_button.setVisible(False)
            if self._session is not None:
                summary = self._session.summary()
                text = f"Готово! Верно: {summary.correct} из {summary.total}"
                if summary.skipped:
                    text += f" (пропущено карточек без текстового ответа: {summary.skipped})"
                self._summary.setText(text)
            return

        if showing_feedback:
            _, feedback, _ = self._pending
            self._verdict.setText(VERDICT_TEXT[feedback.result.verdict.value])
            set_state(self._verdict, "ok" if feedback.is_accepted else "bad")
            self._correct_answer.set_face(feedback.answer)
            self._override_button.setVisible(not feedback.is_accepted)
            return

        self._override_button.setVisible(False)
        prompt = self._session.current()
        self._progress.setText(f"{prompt.index + 1} / {prompt.total}")
        self._prompt.set_face(prompt.prompt)
        self._answer_edit.setFocus()
