"""Тесты разметки граней карточки."""
from qlizmet.core.markup import face_from_markup, face_preview, face_to_markup
from qlizmet.core.models import CardFace, ImageBlock, LatexBlock, TextBlock


def test_plain_text() -> None:
    face = face_from_markup("столица Франции")
    assert face.blocks == (TextBlock("столица Франции"),)
    assert face.is_plain_text


def test_multiline_text_stays_one_block() -> None:
    face = face_from_markup("первая\nвторая")
    assert face.blocks == (TextBlock("первая\nвторая"),)


def test_inline_formula() -> None:
    face = face_from_markup(r"производная $\sin x$ равна")
    assert face.blocks == (
        TextBlock("производная "),
        LatexBlock(r"\sin x"),
        TextBlock(" равна"),
    )


def test_formula_only() -> None:
    face = face_from_markup(r"$\frac{1}{2}$")
    assert face.blocks == (LatexBlock(r"\frac{1}{2}"),)
    assert not face.is_plain_text


def test_two_formulas_in_one_line() -> None:
    face = face_from_markup(r"$a$ и $b$")
    assert [type(b) for b in face.blocks] == [LatexBlock, TextBlock, LatexBlock]


def test_image_line() -> None:
    face = face_from_markup("![карта Европы](europe.png)")
    assert face.blocks == (ImageBlock("europe.png", "карта Европы"),)


def test_image_without_alt() -> None:
    face = face_from_markup("![](pic.png)")
    assert face.blocks == (ImageBlock("pic.png", ""),)


def test_text_and_image_mixed() -> None:
    face = face_from_markup("Что это?\n![](pic.png)")
    assert [type(b) for b in face.blocks] == [TextBlock, ImageBlock]


def test_empty_input() -> None:
    assert face_from_markup("").is_empty
    assert face_from_markup("   \n  ").is_empty


def test_empty_math_is_ignored() -> None:
    # «$$» не должно рождать пустую формулу и падать
    face = face_from_markup("цена $$ важна")
    assert all(not isinstance(b, LatexBlock) for b in face.blocks)


def test_roundtrip_text() -> None:
    markup = "столица Франции"
    assert face_to_markup(face_from_markup(markup)) == markup


def test_roundtrip_mixed() -> None:
    markup = "производная $\\sin x$ равна"
    assert face_to_markup(face_from_markup(markup)) == markup


def test_roundtrip_with_image() -> None:
    markup = "Что это?\n![карта](europe.png)"
    assert face_to_markup(face_from_markup(markup)) == markup


def test_to_markup_from_blocks() -> None:
    face = CardFace((TextBlock("предел "), LatexBlock(r"\lim x")))
    assert face_to_markup(face) == "предел $\\lim x$"


def test_preview_of_text() -> None:
    assert face_preview(CardFace.from_text("Париж")) == "Париж"


def test_preview_marks_non_text() -> None:
    face = CardFace((LatexBlock(r"\cos x"),))
    assert "формула" in face_preview(face)

    image = CardFace((ImageBlock("pic.png", "кот"),))
    assert "кот" in face_preview(image)


def test_preview_of_empty_face() -> None:
    assert face_preview(CardFace()) == "(пусто)"


def test_preview_is_truncated() -> None:
    long_text = "слово " * 40
    preview = face_preview(CardFace.from_text(long_text), limit=20)
    assert len(preview) <= 20
    assert preview.endswith("…")