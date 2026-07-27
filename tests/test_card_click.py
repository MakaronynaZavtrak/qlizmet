"""Клик по карточке переворачивает её так же, как кнопка «Показать ответ»."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QLabel  # noqa: E402

from qlizmet.core.models import Card, CardFace  # noqa: E402
from qlizmet.ui.views.flashcards_view import FlashcardsView  # noqa: E402
from qlizmet.ui.widgets.card_surface import CardSurface  # noqa: E402

CARDS = [
    Card.create(CardFace.from_text("Франция"), CardFace.from_text("Париж")),
    Card.create(CardFace.from_text("Италия"), CardFace.from_text("Рим")),
]


def test_card_emits_clicked_on_left_press(qt_host) -> None:
    surface = CardSurface(QLabel("x"), animated=False, parent=qt_host)
    surface.resize(400, 200)
    fired: list[bool] = []
    surface.clicked.connect(lambda: fired.append(True))

    QTest.mouseClick(surface, Qt.MouseButton.LeftButton)

    assert fired == [True]


def test_click_card_flips(qt_host) -> None:
    view = FlashcardsView(animated=False, parent=qt_host)
    view.start(CARDS, shuffle=False)
    assert not view.answer_shown

    QTest.mouseClick(view._card, Qt.MouseButton.LeftButton)
    assert view.answer_shown

    QTest.mouseClick(view._card, Qt.MouseButton.LeftButton)
    assert not view.answer_shown  # второй клик возвращает вопрос


def test_click_on_card_text_also_flips(qt_host) -> None:
    """Клик прямо по слову тоже переворачивает: текст не перехватывает мышь."""
    view = FlashcardsView(animated=False, parent=qt_host)
    view.start(CARDS, shuffle=False)

    labels = view._face.block_widgets()
    assert labels  # на лице есть текстовый блок
    QTest.mouseClick(labels[0], Qt.MouseButton.LeftButton)

    assert view.answer_shown
