"""Тесты экранов «Заучивание» и «Тест»."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.app.study_service import StudyService  # noqa: E402
from qlizmet.core.models import Card, CardFace, LatexBlock  # noqa: E402
from qlizmet.core.study import QuestionType, TestQuestionType  # noqa: E402
from qlizmet.storage.sqlite.repositories import (  # noqa: E402
    SqliteDeckRepository,
    SqliteProgressRepository,
)
from qlizmet.ui.views.learn_view import LearnView  # noqa: E402
from qlizmet.ui.views.test_view import TestView  # noqa: E402


def _card(front: str, back: str) -> Card:
    return Card.create(CardFace.from_text(front), CardFace.from_text(back))


CARDS = [
    _card("Франция", "Париж"),
    _card("Италия", "Рим"),
    _card("Испания", "Мадрид"),
]
ANSWERS = {card.front.plain_text: card.back.plain_text for card in CARDS}


# --- режим «Заучивание» ---


@pytest.fixture
def learn(qt_host) -> LearnView:
    view = LearnView(parent=qt_host)
    view.start(CARDS, shuffle=False)
    return view


def _learn_correct_index(view: LearnView) -> int:
    """Индекс верного варианта на текущем вопросе."""
    prompt = view.findChild(object, "promptFace").face.plain_text
    expected = ANSWERS[prompt]
    return view.choice_texts().index(expected)


def test_learn_starts_with_choice(learn) -> None:
    assert learn.question_type is QuestionType.CHOICE
    assert len(learn.choice_texts()) > 1


def test_learn_progress_starts_at_zero(learn) -> None:
    assert "0" in learn.progress_text()


def test_learn_correct_choice_gives_verdict(learn) -> None:
    learn.answer_choice(_learn_correct_index(learn))
    assert learn.awaiting_next
    assert learn.verdict_text() == "Верно!"


def test_learn_wrong_choice_shows_correct_answer(learn) -> None:
    correct = _learn_correct_index(learn)
    learn.answer_choice((correct + 1) % len(learn.choice_texts()))
    assert learn.verdict_text() == "Неверно"
    answer = learn.findChild(object, "correctAnswerFace").block_widgets()[0]
    assert answer.text() in ANSWERS.values()


def test_learn_escalates_to_written_after_correct(learn) -> None:
    learn.answer_choice(_learn_correct_index(learn))
    learn.next_question()
    # вернёмся к этой же карточке после круга по остальным
    while learn.findChild(object, "promptFace").face.plain_text != "Франция":
        if learn.question_type is QuestionType.CHOICE:
            learn.answer_choice(_learn_correct_index(learn))
        else:
            learn.findChild(object, "answerEdit").setText("неверно")
            learn.submit_written()
        learn.next_question()
    assert learn.question_type is QuestionType.WRITTEN


def test_learn_written_answer_accepted(learn) -> None:
    learn.answer_choice(_learn_correct_index(learn))
    learn.next_question()
    while learn.question_type is not QuestionType.WRITTEN:
        learn.answer_choice(_learn_correct_index(learn))
        learn.next_question()

    prompt = learn.findChild(object, "promptFace").face.plain_text
    learn.findChild(object, "answerEdit").setText(ANSWERS[prompt])
    learn.submit_written()
    assert learn.verdict_text() == "Верно!"


def test_learn_finishes_when_all_learned(learn) -> None:
    guard = 0
    while not learn.is_finished and guard < 100:
        guard += 1
        if learn.question_type is QuestionType.CHOICE:
            learn.answer_choice(_learn_correct_index(learn))
        else:
            prompt = learn.findChild(object, "promptFace").face.plain_text
            learn.findChild(object, "answerEdit").setText(ANSWERS[prompt])
            learn.submit_written()
        learn.next_question()

    assert learn.is_finished
    assert "3 из 3" in learn.summary_text()


def test_learn_ignores_written_while_asking_choice(learn) -> None:
    learn.submit_written()  # не должно ничего сломать
    assert not learn.awaiting_next


def test_learn_records_progress(conn, qt_host) -> None:
    progress = SqliteProgressRepository(conn)
    library = LibraryService(SqliteDeckRepository(conn))
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")

    view = LearnView(StudyService(progress), parent=qt_host)
    view.start(deck.cards, shuffle=False)
    prompt = view.findChild(object, "promptFace").face.plain_text
    expected = next(c.back.plain_text for c in deck.cards if c.front.plain_text == prompt)
    view.answer_choice(view.choice_texts().index(expected))

    card = next(c for c in deck.cards if c.front.plain_text == prompt)
    assert progress.get(card.id) is not None
    assert progress.reviews_for(card.id)[0].mode == "learn"


def test_learn_option_labels_survive_formulas(qt_host) -> None:
    """Варианты-формулы не должны выглядеть одинаково пустыми."""
    cards = [
        Card.create(CardFace.from_text("производная sin x"), CardFace((LatexBlock(r"\cos x"),))),
        Card.create(CardFace.from_text("производная cos x"), CardFace((LatexBlock(r"-\sin x"),))),
    ]
    view = LearnView(parent=qt_host)
    view.start(cards, shuffle=False)
    labels = view.choice_texts()
    assert len(set(labels)) == len(labels)
    assert all(label.strip() for label in labels)


# --- режим «Тест» ---


@pytest.fixture
def test_view(qt_host) -> TestView:
    view = TestView(parent=qt_host)
    view.start(CARDS)
    return view


def _answer_current_correctly(view: TestView) -> None:
    question = view.current_question
    prompt = question.prompt.plain_text
    expected = ANSWERS[prompt]
    if question.type is TestQuestionType.CHOICE:
        view.answer_choice(view.choice_texts().index(expected))
    elif question.type is TestQuestionType.TRUE_FALSE:
        view.answer_true_false(question.statement.plain_text == expected)
    else:
        view.findChild(object, "answerEdit").setText(expected)
        view.answer_written()


def test_test_shows_first_question(test_view) -> None:
    assert test_view.progress_text() == "1 / 3"
    assert test_view.question_type is not None
    assert not test_view.is_finished


def test_test_advances_through_questions(test_view) -> None:
    _answer_current_correctly(test_view)
    assert test_view.current_index == 1
    assert test_view.progress_text() == "2 / 3"


def test_test_full_correct_run_scores_100(test_view) -> None:
    for _ in range(3):
        _answer_current_correctly(test_view)
    assert test_view.is_finished
    assert test_view.result.correct == 3
    assert "100%" in test_view.score_text()
    assert "Ошибок нет" in test_view.findChild(object, "mistakesLabel").text()


def test_test_wrong_answers_are_listed(qt_host) -> None:
    view = TestView(parent=qt_host)
    view.start(CARDS)
    for _ in range(3):
        question = view.current_question
        if question.type is TestQuestionType.CHOICE:
            view.answer_choice(99)  # заведомо неверный индекс
        elif question.type is TestQuestionType.TRUE_FALSE:
            correct = ANSWERS[question.prompt.plain_text]
            view.answer_true_false(question.statement.plain_text != correct)
        else:
            view.findChild(object, "answerEdit").setText("чепуха")
            view.answer_written()

    assert view.result.correct == 0
    assert "Стоит повторить" in view.findChild(object, "mistakesLabel").text()


def test_test_length_limits_questions(qt_host) -> None:
    view = TestView(parent=qt_host)
    view.start(CARDS, length=2)
    assert view.progress_text() == "1 / 2"


def test_test_wrong_answer_type_is_ignored(test_view) -> None:
    question_type = test_view.question_type
    other = (
        TestQuestionType.WRITTEN
        if question_type is not TestQuestionType.WRITTEN
        else TestQuestionType.CHOICE
    )
    if other is TestQuestionType.WRITTEN:
        test_view.answer_written()
    else:
        test_view.answer_choice(0)
    assert test_view.current_index == 0  # ответ не принят


def test_test_records_progress(conn, qt_host) -> None:
    progress = SqliteProgressRepository(conn)
    library = LibraryService(SqliteDeckRepository(conn))
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")

    view = TestView(StudyService(progress), parent=qt_host)
    view.start(deck.cards)
    answers = {c.front.plain_text: c.back.plain_text for c in deck.cards}
    while not view.is_finished:
        question = view.current_question
        expected = answers[question.prompt.plain_text]
        if question.type is TestQuestionType.CHOICE:
            view.answer_choice(view.choice_texts().index(expected))
        elif question.type is TestQuestionType.TRUE_FALSE:
            view.answer_true_false(question.statement.plain_text == expected)
        else:
            view.findChild(object, "answerEdit").setText(expected)
            view.answer_written()

    for card in deck.cards:
        assert progress.get(card.id) is not None
        assert progress.reviews_for(card.id)[0].mode == "test"