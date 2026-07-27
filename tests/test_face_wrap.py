"""Длинный текст в FaceView переносится и растёт в высоту, а не обрезается."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from PySide6.QtWidgets import QLabel  # noqa: E402

from qlizmet.core.models import CardFace  # noqa: E402
from qlizmet.ui.widgets.face_view import FaceView  # noqa: E402

LONG = "длинный текст с вопросом, в котором содержится много ненужной информации " * 3


def _text_label(view: FaceView) -> QLabel:
    return view.findChild(QLabel, "faceBlockText")


def test_text_label_keeps_full_text(qt_host) -> None:
    view = FaceView(parent=qt_host)
    view.set_face(CardFace.from_text(LONG))
    label = _text_label(view)
    assert label is not None
    assert label.text() == LONG  # текст хранится целиком
    assert label.wordWrap()


def test_text_label_height_follows_width(qt_host) -> None:
    """Метка учитывает heightForWidth: узкая ширина -> много строк."""
    view = FaceView(parent=qt_host)
    view.set_face(CardFace.from_text(LONG))
    label = _text_label(view)
    assert label.sizePolicy().hasHeightForWidth()
    one_line = label.fontMetrics().height()
    # при узкой ширине перенос даёт заметно больше одной строки
    assert label.heightForWidth(260) > one_line * 3


def test_short_text_stays_centered_single_line(qt_host) -> None:
    view = FaceView(parent=qt_host)
    view.set_face(CardFace.from_text("коротко"))
    label = _text_label(view)
    one_line = label.fontMetrics().height()
    # короткий текст остаётся в одну строку
    assert label.heightForWidth(600) <= one_line * 2
