"""Тесты доступности режимов."""
from qlizmet.core.models import Card, CardFace, LatexBlock
from qlizmet.core.study import (
    Direction,
    StudyMode,
    available_modes,
    mode_availability,
    typed_answer_count,
)


def _text_card(front: str, back: str) -> Card:
    return Card.create(CardFace.from_text(front), CardFace.from_text(back))


def _latex_card() -> Card:
    return Card.create(CardFace.from_text("производная sin x"), CardFace((LatexBlock(r"\cos x"),)))


def test_empty_deck_allows_nothing() -> None:
    assert available_modes([]) == set()


def test_single_text_card_allows_flashcards_and_write() -> None:
    modes = available_modes([_text_card("Франция", "Париж")])
    assert StudyMode.FLASHCARDS in modes
    assert StudyMode.WRITE in modes
    assert StudyMode.MATCH not in modes  # игре нужна пара карточек
    assert StudyMode.LEARN not in modes


def test_two_text_cards_allow_everything() -> None:
    cards = [_text_card("Франция", "Париж"), _text_card("Италия", "Рим")]
    assert available_modes(cards) == set(StudyMode)


def test_formula_answers_block_typed_modes() -> None:
    cards = [_latex_card(), _latex_card()]
    modes = available_modes(cards)
    assert StudyMode.WRITE not in modes
    assert StudyMode.GRAVITY not in modes
    assert StudyMode.FLASHCARDS in modes
    assert StudyMode.MATCH in modes


def test_direction_changes_availability() -> None:
    # ответ-формула мешает вводу, но в обратную сторону ответ уже текстовый
    cards = [_latex_card()]
    assert StudyMode.WRITE not in available_modes(cards)
    assert StudyMode.WRITE in available_modes(cards, Direction.BACK_TO_FRONT)


def test_typed_answer_count() -> None:
    cards = [_text_card("a", "b"), _latex_card()]
    assert typed_answer_count(cards) == 1


def test_reasons_are_explained() -> None:
    reasons = mode_availability([_latex_card()])
    assert reasons[StudyMode.FLASHCARDS] is None
    assert "текстовый" in reasons[StudyMode.WRITE]
    assert "2" in reasons[StudyMode.MATCH]


def test_mode_titles_are_human() -> None:
    assert StudyMode.FLASHCARDS.title == "Карточки"
    assert StudyMode.WRITE.title == "Письмо"