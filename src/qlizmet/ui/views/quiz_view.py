"""Экран режима «Тест».

Билет генерируется целиком заранее (``TestSession``), человек проходит вопросы
один за другим, а проверка и подсчёт очков происходят в конце — как на настоящем
тесте, без подсказок по ходу.

Результаты записываются в прогресс уже после проверки, одним заходом: до неё
неизвестно, какие ответы верны.
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
from qlizmet.core.models import Card
from qlizmet.core.srs import Grade
from qlizmet.core.study import (
    Direction,
    TestQuestionType,
    TestResult,
    TestSession,
)
from qlizmet.ui.widgets.face_view import FaceView

MAX_CHOICES = 4
DEFAULT_LENGTH = 20


class TestView(QWidget):
    """Прохождение теста с проверкой в конце."""

    __test__ = False  # это экран приложения, а не тест-класс pytest

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
        self._session: TestSession | None = None
        self._index = 0
        self._result: TestResult | None = None

        back = QPushButton("← Выйти")
        back.setObjectName("backButton")
        back.clicked.connect(self.back_requested.emit)

        self._progress = QLabel()
        self._progress.setObjectName("progressLabel")
        self._progress.setAlignment(Qt.AlignmentFlag.AlignRight)

        header = QHBoxLayout()
        header.addWidget(back)
        header.addWidget(self._progress, stretch=1)

        self._kind_label = QLabel()
        self._kind_label.setObjectName("kindLabel")
        self._kind_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._prompt = FaceView(media_root=media_root)
        self._prompt.setObjectName("promptFace")

        # выбор варианта
        self._choice_buttons: list[QPushButton] = []
        choices = QVBoxLayout()
        for index in range(MAX_CHOICES):
            button = QPushButton()
            button.setObjectName(f"choice_{index}")
            button.setMinimumHeight(40)
            button.clicked.connect(lambda _checked=False, i=index: self.answer_choice(i))
            self._choice_buttons.append(button)
            choices.addWidget(button)
        self._choices_box = QWidget()
        self._choices_box.setObjectName("choicesBox")
        self._choices_box.setLayout(choices)

        # верно / неверно
        self._statement = FaceView(media_root=media_root)
        self._statement.setObjectName("statementFace")

        self._true_button = QPushButton("Верно")
        self._true_button.setObjectName("trueButton")
        self._true_button.clicked.connect(lambda: self.answer_true_false(True))

        self._false_button = QPushButton("Неверно")
        self._false_button.setObjectName("falseButton")
        self._false_button.clicked.connect(lambda: self.answer_true_false(False))

        true_false = QHBoxLayout()
        true_false.addWidget(self._true_button)
        true_false.addWidget(self._false_button)
        self._true_false_box = QWidget()
        self._true_false_box.setObjectName("trueFalseBox")
        self._true_false_box.setLayout(true_false)

        # ввод ответа
        self._answer_edit = QLineEdit()
        self._answer_edit.setObjectName("answerEdit")
        self._answer_edit.setPlaceholderText("Ваш ответ")
        self._answer_edit.returnPressed.connect(self.answer_written)

        self._submit_button = QPushButton("Ответить")
        self._submit_button.setObjectName("submitButton")
        self._submit_button.clicked.connect(self.answer_written)

        # результат
        self._score = QLabel()
        self._score.setObjectName("scoreLabel")
        self._score.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._mistakes = QLabel()
        self._mistakes.setObjectName("mistakesLabel")
        self._mistakes.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mistakes.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addStretch(1)
        layout.addWidget(self._kind_label)
        layout.addWidget(self._prompt)
        layout.addWidget(self._statement)
        layout.addWidget(self._choices_box)
        layout.addWidget(self._true_false_box)
        layout.addWidget(self._answer_edit)
        layout.addWidget(self._submit_button)
        layout.addWidget(self._score)
        layout.addWidget(self._mistakes)
        layout.addStretch(1)
        self.setLayout(layout)

    # --- управление сессией ---

    def start(
        self,
        cards: Sequence[Card],
        *,
        length: int = DEFAULT_LENGTH,
        direction: Direction = Direction.FRONT_TO_BACK,
    ) -> None:
        self._session = TestSession(cards, length=length, direction=direction)
        self._index = 0
        self._result = None
        self._answer_edit.clear()
        self._refresh()

    @property
    def is_finished(self) -> bool:
        return self._result is not None

    @property
    def current_index(self) -> int:
        return self._index

    @property
    def result(self) -> TestResult | None:
        return self._result

    @property
    def current_question(self):
        """Текущий вопрос билета или ``None``, если тест окончен."""
        return self._current_question()

    @property
    def question_type(self) -> TestQuestionType | None:
        question = self._current_question()
        return question.type if question else None

    def answer_choice(self, index: int) -> None:
        self._record_answer(TestQuestionType.CHOICE, index)

    def answer_true_false(self, value: bool) -> None:
        self._record_answer(TestQuestionType.TRUE_FALSE, value)

    def answer_written(self) -> None:
        self._record_answer(TestQuestionType.WRITTEN, self._answer_edit.text())

    def score_text(self) -> str:
        return self._score.text()

    def progress_text(self) -> str:
        return self._progress.text()

    def choice_texts(self) -> list[str]:
        return [
            button.text()
            for button in self._choice_buttons
            if button.isVisibleTo(self._choices_box)
        ]

    # --- внутреннее ---

    def _current_question(self):
        if self._session is None or self._result is not None:
            return None
        if self._index >= self._session.total:
            return None
        return self._session.questions[self._index]

    def _record_answer(self, expected: TestQuestionType, response: object) -> None:
        question = self._current_question()
        if question is None or question.type is not expected:
            return
        self._session.answer(self._index, response)
        self._index += 1
        self._answer_edit.clear()
        if self._index >= self._session.total:
            self._finish()
        else:
            self._refresh()

    def _finish(self) -> None:
        self._result = self._session.grade()
        if self._study is not None:
            for item in self._result.items:
                self._study.record(
                    item.card_id,
                    Grade.GOOD if item.is_correct else Grade.AGAIN,
                    mode="test",
                )
        self._refresh()

    def _refresh(self) -> None:
        question = self._current_question()
        finished = self._result is not None

        for widget in (
            self._kind_label,
            self._prompt,
            self._statement,
            self._choices_box,
            self._true_false_box,
            self._answer_edit,
            self._submit_button,
        ):
            widget.setVisible(False)
        self._score.setVisible(finished)
        self._mistakes.setVisible(finished)

        if finished:
            self._progress.setText("")
            result = self._result
            self._score.setText(
                f"Результат: {result.correct} из {result.total} "
                f"({round(result.score * 100)}%)"
            )
            wrong = [item for item in result.items if not item.is_correct]
            self._mistakes.setText(
                "Ошибок нет — отлично!"
                if not wrong
                else "Стоит повторить: "
                + ", ".join(face_preview(item.correct_answer, 24) for item in wrong)
            )
            return

        if question is None:
            return

        self._progress.setText(f"{self._index + 1} / {self._session.total}")
        self._kind_label.setVisible(True)
        self._prompt.setVisible(True)
        self._prompt.set_face(question.prompt)

        if question.type is TestQuestionType.CHOICE:
            self._kind_label.setText("Выберите верный ответ")
            self._choices_box.setVisible(True)
            for index, button in enumerate(self._choice_buttons):
                has_option = index < len(question.options)
                button.setVisible(has_option)
                if has_option:
                    button.setText(face_preview(question.options[index]))
        elif question.type is TestQuestionType.TRUE_FALSE:
            self._kind_label.setText("Верно ли утверждение?")
            self._statement.setVisible(True)
            self._statement.set_face(question.statement)
            self._true_false_box.setVisible(True)
        else:
            self._kind_label.setText("Напишите ответ")
            self._answer_edit.setVisible(True)
            self._submit_button.setVisible(True)
            self._answer_edit.setFocus()
