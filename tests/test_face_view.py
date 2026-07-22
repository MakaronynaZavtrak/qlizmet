"""Тесты виджета FaceView (headless, offscreen-платформа)."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from qlizmet.core.models import CardFace, ImageBlock, LatexBlock, TextBlock  # noqa: E402
from qlizmet.ui.widgets.face_view import FaceView  # noqa: E402


def _names(view: FaceView) -> list[str]:
    return [w.objectName() for w in view.block_widgets()]


def test_empty_face_has_no_blocks(qt_host) -> None:
    view = FaceView(CardFace(), parent=qt_host)
    assert view.block_widgets() == ()


def test_text_block_is_rendered(qt_host) -> None:
    view = FaceView(CardFace.from_text("столица Франции"), parent=qt_host)
    widgets = view.block_widgets()
    assert len(widgets) == 1
    assert widgets[0].objectName() == "faceBlockText"
    assert widgets[0].text() == "столица Франции"


def test_latex_block_becomes_pixmap(qt_host) -> None:
    view = FaceView(CardFace((LatexBlock(r"\frac{1}{2}"),)), parent=qt_host)
    label = view.block_widgets()[0]
    assert label.objectName() == "faceBlockLatex"
    assert not label.pixmap().isNull()


def test_broken_latex_falls_back_to_source(qt_host) -> None:
    view = FaceView(CardFace((LatexBlock(r"\frac{1}{"),)), parent=qt_host)
    label = view.block_widgets()[0]
    assert label.objectName() == "faceBlockLatexError"
    assert r"\frac{1}{" in label.text()


def test_missing_image_shows_alt(qt_host) -> None:
    face = CardFace((ImageBlock("нет-такого.png", alt="карта Европы"),))
    view = FaceView(face, parent=qt_host)
    label = view.block_widgets()[0]
    assert label.objectName() == "faceBlockImageMissing"
    assert "карта Европы" in label.text()


def test_existing_image_is_loaded(qt_host, tmp_path) -> None:
    from PySide6.QtGui import QPixmap

    media = tmp_path / "media"
    media.mkdir()
    source = QPixmap(64, 32)
    source.fill()
    source.save(str(media / "pic.png"), "PNG")

    face = CardFace((ImageBlock("pic.png", alt="картинка"),))
    view = FaceView(face, media_root=media, parent=qt_host)
    label = view.block_widgets()[0]
    assert label.objectName() == "faceBlockImage"
    assert not label.pixmap().isNull()


def test_wide_image_is_scaled_down(qt_host, tmp_path) -> None:
    from PySide6.QtGui import QPixmap

    media = tmp_path / "media"
    media.mkdir()
    source = QPixmap(1000, 200)
    source.fill()
    source.save(str(media / "wide.png"), "PNG")

    view = FaceView(
        CardFace((ImageBlock("wide.png"),)),
        media_root=media,
        max_image_width=300,
        parent=qt_host,
    )
    assert view.block_widgets()[0].pixmap().width() == 300


def test_mixed_face_preserves_order(qt_host) -> None:
    face = CardFace(
        (TextBlock("производная "), LatexBlock(r"\sin x"), ImageBlock("нет.png"))
    )
    view = FaceView(face, parent=qt_host)
    assert _names(view) == [
        "faceBlockText",
        "faceBlockLatex",
        "faceBlockImageMissing",
    ]


def test_set_face_replaces_content(qt_host) -> None:
    view = FaceView(CardFace.from_text("первая"), parent=qt_host)
    view.set_face(CardFace.from_text("вторая"))
    widgets = view.block_widgets()
    assert len(widgets) == 1
    assert widgets[0].text() == "вторая"
    assert view.face.plain_text == "вторая"