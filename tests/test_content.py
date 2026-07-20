"""Тесты блоков содержимого и CardFace."""
import dataclasses

import pytest

from qlizmet.core.models import CardFace, ImageBlock, LatexBlock, TextBlock


def test_blocks_are_frozen() -> None:
    block = TextBlock("привет")
    with pytest.raises(dataclasses.FrozenInstanceError):
        block.text = "изменено"  # type: ignore[misc]


def test_latex_block_rejects_empty() -> None:
    with pytest.raises(ValueError):
        LatexBlock("   ")


def test_image_block_rejects_empty_path() -> None:
    with pytest.raises(ValueError):
        ImageBlock("")


def test_image_block_keeps_alt() -> None:
    block = ImageBlock("media/cat.png", alt="кот")
    assert block.path == "media/cat.png"
    assert block.alt == "кот"


def test_from_text_is_plain_text() -> None:
    face = CardFace.from_text("столица Франции")
    assert face.is_plain_text
    assert face.plain_text == "столица Франции"


def test_mixed_face_is_not_plain_text() -> None:
    face = CardFace((TextBlock("предел "), LatexBlock(r"\lim_{x\to 0}")))
    assert not face.is_plain_text
    assert face.plain_text == "предел "


def test_empty_face() -> None:
    face = CardFace()
    assert face.is_empty
    assert not face.is_plain_text


def test_identical_faces_are_equal() -> None:
    a = CardFace.from_text("одно и то же")
    b = CardFace.from_text("одно и то же")
    assert a == b