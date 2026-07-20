"""Тесты сериализации граней, тегов и дат."""
from datetime import datetime, timezone

from qlizmet.core.models import CardFace, ImageBlock, LatexBlock, TextBlock
from qlizmet.storage.serialization import (
    dt_from_iso,
    dt_to_iso,
    face_from_json,
    face_to_json,
    tags_from_json,
    tags_to_json,
)


def test_text_face_roundtrip() -> None:
    face = CardFace.from_text("столица Франции")
    assert face_from_json(face_to_json(face)) == face


def test_latex_face_roundtrip() -> None:
    face = CardFace((LatexBlock(r"\lim_{x\to 0}\frac{\sin x}{x}"),))
    assert face_from_json(face_to_json(face)) == face


def test_image_face_roundtrip_keeps_alt() -> None:
    face = CardFace((ImageBlock("media/map.png", alt="карта"),))
    restored = face_from_json(face_to_json(face))
    assert restored == face
    assert restored.blocks[0].alt == "карта"


def test_mixed_face_preserves_order_and_types() -> None:
    face = CardFace(
        (TextBlock("предел "), LatexBlock(r"\sin x"), ImageBlock("media/x.png"))
    )
    restored = face_from_json(face_to_json(face))
    assert restored == face
    assert [type(b) for b in restored.blocks] == [TextBlock, LatexBlock, ImageBlock]


def test_tags_roundtrip() -> None:
    tags = ("гео", "столицы")
    assert tags_from_json(tags_to_json(tags)) == tags


def test_datetime_roundtrip() -> None:
    now = datetime(2026, 1, 10, 12, 30, tzinfo=timezone.utc)
    assert dt_from_iso(dt_to_iso(now)) == now


def test_none_datetime_roundtrip() -> None:
    assert dt_to_iso(None) is None
    assert dt_from_iso(None) is None