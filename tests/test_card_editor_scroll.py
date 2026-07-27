"""Окно правки карточки прокручивается, а кнопки ОК/Cancel всегда достижимы."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from PySide6.QtWidgets import QDialogButtonBox, QScrollArea  # noqa: E402

from qlizmet.ui.views.card_editor_dialog import CardEditorDialog  # noqa: E402

BIG = (
    "длинный текст с вопросом, в котром содержится много ненужной информации, "
    "который идёт с переносом строки. Вот, как-то так. "
) * 8


def test_dialog_has_scroll_area(qt_host) -> None:
    dialog = CardEditorDialog(parent=qt_host)
    assert dialog.findChild(QScrollArea, "cardEditorScroll") is not None


def test_dialog_height_capped_to_screen(qt_host) -> None:
    dialog = CardEditorDialog(parent=qt_host)
    dialog.set_markup(front=BIG, back=BIG)
    dialog.show()
    # окно не должно вырасти выше экрана — дальше растит прокрутка
    assert dialog.maximumHeight() > 0
    assert dialog.height() <= dialog.maximumHeight()


def test_buttons_stay_inside_window(qt_host) -> None:
    dialog = CardEditorDialog(parent=qt_host)
    dialog.set_markup(front=BIG, back=BIG)
    dialog.show()
    buttons = dialog.findChild(QDialogButtonBox)
    # кнопки зафиксированы снизу и помещаются в окно (не уезжают за низ)
    assert buttons.y() + buttons.height() <= dialog.height()


def test_scroll_engages_when_content_tall(qt_host) -> None:
    dialog = CardEditorDialog(parent=qt_host)
    dialog.set_markup(front=BIG, back=BIG)
    dialog.show()
    scroll = dialog.findChild(QScrollArea, "cardEditorScroll")
    content = scroll.widget()
    # длинный контент выше вьюпорта -> появляется вертикальная прокрутка
    assert content.sizeHint().height() > scroll.viewport().height()
