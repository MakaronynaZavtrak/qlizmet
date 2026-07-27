"""Перенос текста в кнопках-вариантах, скролл и отсутствие обрезки."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from PySide6.QtWidgets import QScrollArea  # noqa: E402

from qlizmet.core.models import Card, CardFace  # noqa: E402
from qlizmet.ui.views.learn_view import LearnView  # noqa: E402
from qlizmet.ui.views.quiz_view import TestView  # noqa: E402
from qlizmet.ui.widgets.choice_button import ChoiceButton  # noqa: E402

LONG = (
    "Значит ты больной еблан и вообще довольно длинный ответ, "
    "который обязан переноситься на несколько строк и не обрезаться"
)


def test_choice_button_grows_with_wrapped_text(qt_host) -> None:
    short = ChoiceButton(parent=qt_host)
    short.set_text("пых")
    long = ChoiceButton(parent=qt_host)
    long.set_text(LONG)
    # при одной и той же (узкой) ширине длинный текст даёт бóльшую высоту
    assert long.heightForWidth(220) > short.heightForWidth(220)


def test_choice_button_switches_between_text_and_formula(qt_host) -> None:
    from qlizmet.ui.formula import formula_pixmap

    button = ChoiceButton(parent=qt_host)
    button.set_text("привет")
    assert not button.is_formula()
    assert button.displayed_text() == "привет"

    pixmap = formula_pixmap(r"\frac{1}{2}", "#e6e8ec", 28)
    button.set_formula(pixmap)
    assert button.is_formula()
    assert button.displayed_text() == ""


def test_learn_view_has_scroll(qt_host) -> None:
    view = LearnView(parent=qt_host)
    assert view.findChild(QScrollArea, "learnScroll") is not None


def test_quiz_view_has_scroll(qt_host) -> None:
    view = TestView(parent=qt_host)
    assert view.findChild(QScrollArea, "quizScroll") is not None


def test_long_option_text_is_not_truncated(qt_host) -> None:
    """Длинный вариант хранится целиком — без «…» из компактного превью."""
    cards = [
        Card.create(CardFace.from_text("вопрос один"), CardFace.from_text(LONG)),
        Card.create(CardFace.from_text("вопрос два"), CardFace.from_text("короткий")),
    ]
    view = LearnView(parent=qt_host)
    view.start(cards, shuffle=False)
    assert LONG in view.choice_texts()  # полный текст, не обрезанный
    assert not any("…" in label for label in view.choice_texts())
