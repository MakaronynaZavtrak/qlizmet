"""Варианты-формулы на кнопках выбора рисуются картинкой, а не сырым LaTeX."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from qlizmet.core.models import Card, CardFace, LatexBlock, TextBlock  # noqa: E402
from qlizmet.ui.formula import formula_pixmap, single_formula  # noqa: E402
from qlizmet.ui.views.learn_view import LearnView  # noqa: E402


# --- общий модуль ui/formula.py ---


def test_single_formula_detects_pure_formula() -> None:
    assert single_formula(CardFace((LatexBlock(r"\cos x"),))) == r"\cos x"


def test_single_formula_none_for_text() -> None:
    assert single_formula(CardFace.from_text("Париж")) is None


def test_single_formula_none_for_mixed() -> None:
    mixed = CardFace((TextBlock("значение"), LatexBlock(r"x")))
    assert single_formula(mixed) is None


def test_formula_pixmap_renders_valid(qt_host) -> None:
    pixmap = formula_pixmap(r"\frac{1}{2}", "#e6e8ec", 28)
    assert pixmap is not None and not pixmap.isNull()
    assert pixmap.height() <= 28


def test_formula_pixmap_none_for_broken(qt_host) -> None:
    assert formula_pixmap(r"\frac{", "#e6e8ec", 28) is None


# --- экран «Заучивание»: первый вопрос всегда выбор ---


def _visible_choices(view: LearnView) -> list:
    box = view.findChild(object, "choicesBox")
    return [
        button
        for i in range(4)
        if (button := view.findChild(object, f"choice_{i}")) is not None
        and button.isVisibleTo(box)
    ]


def test_learn_formula_option_shows_icon_not_text(qt_host) -> None:
    cards = [
        Card.create(CardFace.from_text("производная sin x"), CardFace((LatexBlock(r"\cos x"),))),
        Card.create(CardFace.from_text("производная cos x"), CardFace((LatexBlock(r"-\sin x"),))),
    ]
    view = LearnView(parent=qt_host)
    view.start(cards, shuffle=False)

    formula_buttons = [b for b in _visible_choices(view) if not b.icon().isNull()]
    assert formula_buttons  # хотя бы один вариант нарисован формулой
    for button in formula_buttons:
        assert button.text() == ""  # на кнопке-формуле текста нет

    # но осмысленные подписи для логики/тестов сохраняются
    labels = view.choice_texts()
    assert all(label.strip() for label in labels)
    assert len(set(labels)) == len(labels)


def test_learn_text_option_stays_text(qt_host) -> None:
    view = LearnView(parent=qt_host)
    view.start(
        [
            Card.create(CardFace.from_text("Франция"), CardFace.from_text("Париж")),
            Card.create(CardFace.from_text("Италия"), CardFace.from_text("Рим")),
        ],
        shuffle=False,
    )
    for button in _visible_choices(view):
        assert button.icon().isNull()  # текстовые варианты — без иконки
        assert button.text().strip()
