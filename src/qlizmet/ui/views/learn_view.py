"""Экран режима «Заучивание».

Ведёт карточки к состоянию «выучено»: сначала спрашивает выбором варианта, после
первого верного ответа поднимает до ввода текста, при ошибке возвращает обратно.
Вся эта логика живёт в ``LearnSession`` из ядра — экран только рисует её
состояние и передаёт ответы.

В отличие от «Письма», здесь нет кнопки «я был прав», поэтому результат
записывается сразу после ответа, а не откладывается до перехода дальше.
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

from qlizmet.app.study_service import StudyService
from qlizmet.core.markup import face_preview
from qlizmet.core.models import Card, CardProgress
from qlizmet.core.study import (
    Direction,
    LearnFeedback,
    LearnSession,
    QuestionType,
)
from qlizmet.ui.theme import GAP, PAD, set_state
from qlizmet.ui.widgets.face_view import FaceView

MAX_CHOICES = 4


class LearnView(QWidget):
    """Адаптивное заучивание с вариантами и вводом ответа."""

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
        self._session: LearnSession | None = None
        self._pending: LearnFeedback | None = None

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

        # варианты ответа: кнопки создаём заранее, лишние прячем
        self._choice_buttons: list[QPushButton] = []
        choices = QVBoxLayout()
        for index in range(MAX_CHOICES):
            button = QPushButton()
            button.setObjectName(f"choice_{index}")
            button.setMinimumHeight(40)
            button.clicked.connect(
                lambda _checked=False, i=index: self.answer_choice(i)
            )
            self._choice_buttons.append(button)
            choices.addWidget(button)
        self._choices_box = QWidget()
        self._choices_box.setObjectName("choicesBox")
        self._choices_box.setLayout(choices)

        self._answer_edit = QLineEdit()
        self._answer_edit.setObjectName("answerEdit")
        self._answer_edit.setPlaceholderText("Ваш ответ")
        self._answer_edit.returnPressed.connect(self.submit_written)

        self._submit_button = QPushButton("Ответить")
        self._submit_button.setObjectName("submitButton")
        self._submit_button.clicked.connect(self.submit_written)

        self._verdict = QLabel()
        self._verdict.setObjectName("verdictLabel")
        self._verdict.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._correct_answer = FaceView(media_root=media_root)
        self._correct_answer.setObjectName("correctAnswerFace")

        self._next_button = QPushButton("Дальше")
        self._next_button.setObjectName("nextButton")
        self._next_button.clicked.connect(self.next_question)

        self._summary = QLabel()
        self._summary.setObjectName("summaryLabel")
        self._summary.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.setContentsMargins(PAD, PAD, PAD, PAD)
        layout.setSpacing(GAP)
        layout.addLayout(header)
        layout.addStretch(1)
        layout.addWidget(self._prompt)
        layout.addWidget(self._choices_box)
        layout.addWidget(self._answer_edit)
        layout.addWidget(self._submit_button)
        layout.addWidget(self._verdict)
        layout.addWidget(self._correct_answer)
        layout.addWidget(self._summary)
        layout.addStretch(1)
        layout.addWidget(self._next_button)
        self.setLayout(layout)

    # --- управление сессией ---

    def start(
        self,
        cards: Sequence[Card],
        *,
        direction: Direction = Direction.FRONT_TO_BACK,
        progress: dict[str, CardProgress] | None = None,
        shuffle: bool = True,
    ) -> None:
        self._session = LearnSession(
            cards, direction=direction, progress=progress, shuffle=shuffle
        )
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
        return self._pending is not None

    @property
    def question_type(self) -> QuestionType | None:
        if self._session is None:
            return None
        question = self._session.current()
        return question.type if question else None

    def answer_choice(self, index: int) -> None:
        if self._session is None or self._pending is not None:
            return
        question = self._session.current()
        if question is None or question.type is not QuestionType.CHOICE:
            return
        self._handle(self._session.answer_choice(index))

    def submit_written(self) -> None:
        if self._session is None or self._pending is not None:
            return
        question = self._session.current()
        if question is None or question.type is not QuestionType.WRITTEN:
            return
        text = self._answer_edit.text()
        self._handle(self._session.answer_written(text), user_answer=text)

    def next_question(self) -> None:
        if self._pending is None:
            return
        self._pending = None
        self._answer_edit.clear()
        self._refresh()

    def verdict_text(self) -> str:
        return self._verdict.text()

    def progress_text(self) -> str:
        return self._progress.text()

    def summary_text(self) -> str:
        return self._summary.text()

    def choice_texts(self) -> list[str]:
        """Подписи видимых вариантов (удобно для тестов)."""
        return [
            button.text()
            for button in self._choice_buttons
            if button.isVisibleTo(self._choices_box)
        ]

    # --- внутреннее ---

    def _handle(self, feedback: LearnFeedback, user_answer: str | None = None) -> None:
        self._pending = feedback
        if self._study is not None:
            self._study.record(
                feedback.card_id,
                feedback.grade,
                mode="learn",
                user_answer=user_answer,
            )
        self._refresh()

    def _refresh(self) -> None:
        session = self._session
        finished = self.is_finished
        showing_feedback = self._pending is not None
        question = session.current() if session and not session.is_finished else None

        self._summary.setVisible(finished)
        self._prompt.setVisible(not finished)
        self._verdict.setVisible(showing_feedback)
        self._correct_answer.setVisible(showing_feedback)
        self._next_button.setVisible(showing_feedback)

        asking_choice = (
            not finished
            and not showing_feedback
            and question is not None
            and question.type is QuestionType.CHOICE
        )
        asking_written = (
            not finished
            and not showing_feedback
            and question is not None
            and question.type is QuestionType.WRITTEN
        )
        self._choices_box.setVisible(asking_choice)
        self._answer_edit.setVisible(asking_written)
        self._submit_button.setVisible(asking_written)

        if session is not None:
            summary = session.summary()
            self._progress.setText(
                f"выучено {summary.learned} / {summary.total}"
            )

        if finished:
            self._progress.setText("")
            if session is not None:
                summary = session.summary()
                self._summary.setText(
                    f"Готово! Выучено {summary.learned} из {summary.total} "
                    f"за {summary.questions_asked} вопр."
                )
            return

        if showing_feedback:
            feedback = self._pending
            self._verdict.setText("Верно!" if feedback.is_correct else "Неверно")
            set_state(self._verdict, "ok" if feedback.is_correct else "bad")
            self._correct_answer.set_face(feedback.correct_answer)
            return

        self._prompt.set_face(question.prompt)
        if asking_choice:
            for index, button in enumerate(self._choice_buttons):
                has_option = index < len(question.options)
                button.setVisible(has_option)
                if has_option:
                    # face_preview, а не plain_text: у формул и картинок текст пустой,
                    # и такие варианты были бы неотличимы друг от друга
                    button.setText(face_preview(question.options[index]))
        else:
            self._answer_edit.setFocus()
