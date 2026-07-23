"""Тесты экранов обучения: выбор режима, «Карточки», «Письмо»."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from qlizmet.app.deck_service import DeckService  # noqa: E402
from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.app.study_service import StudyService  # noqa: E402
from qlizmet.core.models import Card, CardFace, LatexBlock  # noqa: E402
from qlizmet.core.study import StudyMode  # noqa: E402
from qlizmet.storage.sqlite.repositories import (  # noqa: E402
    SqliteDeckRepository,
    SqliteProgressRepository,
)
from qlizmet.ui.views.flashcards_view import FlashcardsView  # noqa: E402
from qlizmet.ui.views.mode_select_view import ModeSelectView  # noqa: E402
from qlizmet.ui.views.write_view import WriteView  # noqa: E402


def _card(front: str, back: str) -> Card:
    return Card.create(CardFace.from_text(front), CardFace.from_text(back))


CARDS = [_card("Франция", "Париж"), _card("Италия", "Рим")]


# --- выбор режима ---


@pytest.fixture
def services(conn):
    repo = SqliteDeckRepository(conn)
    return LibraryService(repo), DeckService(repo)


def test_modes_enabled_for_text_deck(services, qt_host) -> None:
    library, decks = services
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")
    view = ModeSelectView(decks, {StudyMode.FLASHCARDS, StudyMode.WRITE}, parent=qt_host)
    view.load(deck.id)

    assert view.enabled_modes() == {StudyMode.FLASHCARDS, StudyMode.WRITE}


def test_unimplemented_mode_is_disabled_with_hint(services, qt_host) -> None:
    library, decks = services
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")
    view = ModeSelectView(decks, {StudyMode.FLASHCARDS}, parent=qt_host)
    view.load(deck.id)

    button = view.button_for(StudyMode.MATCH)
    assert not button.isEnabled()
    assert button.toolTip()


def test_write_disabled_when_answers_are_formulas(services, qt_host) -> None:
    library, decks = services
    deck = library.create("Матан")
    for _ in range(2):
        decks.add_card(
            deck.id,
            CardFace.from_text("производная sin x"),
            CardFace((LatexBlock(r"\cos x"),)),
        )
    view = ModeSelectView(decks, parent=qt_host)
    view.load(deck.id)

    assert StudyMode.WRITE not in view.enabled_modes()
    assert StudyMode.FLASHCARDS in view.enabled_modes()
    assert "текстовый" in view.button_for(StudyMode.WRITE).toolTip()


def test_mode_selection_emits_value(services, qt_host) -> None:
    library, decks = services
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")
    view = ModeSelectView(decks, {StudyMode.FLASHCARDS}, parent=qt_host)
    view.load(deck.id)

    chosen: list[str] = []
    view.mode_selected.connect(chosen.append)
    view.button_for(StudyMode.FLASHCARDS).click()
    assert chosen == ["flashcards"]


# --- режим «Карточки» ---


@pytest.fixture
def flashcards(qt_host) -> FlashcardsView:
    # анимация выключена: тесты проверяют состояние, а не время
    view = FlashcardsView(animated=False, parent=qt_host)
    view.start(CARDS, shuffle=False)
    return view


def test_flashcards_show_question_first(flashcards) -> None:
    assert not flashcards.answer_shown
    assert flashcards.progress_text() == "1 / 2"
    label = flashcards.findChild(object, "cardFace").block_widgets()[0]
    assert label.text() == "Франция"


def test_flashcards_flip_shows_answer(flashcards) -> None:
    flashcards.flip()
    assert flashcards.answer_shown
    label = flashcards.findChild(object, "cardFace").block_widgets()[0]
    assert label.text() == "Париж"


def test_flashcards_flip_back(flashcards) -> None:
    flashcards.flip()
    flashcards.flip()
    assert not flashcards.answer_shown


def test_flashcards_mark_advances_and_resets_side(flashcards) -> None:
    flashcards.flip()
    flashcards.mark(known=True)
    assert not flashcards.answer_shown
    assert flashcards.progress_text() == "2 / 2"


def test_flashcards_finish_shows_summary(flashcards) -> None:
    flashcards.mark(known=True)
    flashcards.mark(known=False)
    assert flashcards.is_finished
    assert "1 из 2" in flashcards.summary_text()


def test_flashcards_ignore_actions_after_finish(flashcards) -> None:
    flashcards.mark(True)
    flashcards.mark(True)
    flashcards.mark(True)  # не должно падать
    flashcards.flip()
    assert flashcards.is_finished


# --- режим «Письмо» ---


@pytest.fixture
def write(qt_host) -> WriteView:
    view = WriteView(parent=qt_host)
    view.start(CARDS, shuffle=False)
    return view


def _type(view: WriteView, text: str) -> None:
    view.findChild(object, "answerEdit").setText(text)


def test_write_shows_prompt(write) -> None:
    assert write.progress_text() == "1 / 2"
    label = write.findChild(object, "promptFace").block_widgets()[0]
    assert label.text() == "Франция"


def test_write_correct_answer(write) -> None:
    _type(write, "париж")
    write.submit()
    assert write.awaiting_next
    assert write.verdict_text() == "Верно!"


def test_write_typo_is_accepted(write) -> None:
    _type(write, "Париш")
    write.submit()
    assert "опечат" in write.verdict_text()


def test_write_wrong_answer_shows_correct(write) -> None:
    _type(write, "Лондон")
    write.submit()
    assert write.verdict_text() == "Неверно"
    answer = write.findChild(object, "correctAnswerFace").block_widgets()[0]
    assert answer.text() == "Париж"
    assert write.findChild(object, "overrideButton").isVisibleTo(write)


def test_write_override_flips_verdict(write) -> None:
    _type(write, "Лондон")
    write.submit()
    write.override()
    assert write.verdict_text() == "Верно!"


def test_write_next_advances(write) -> None:
    _type(write, "париж")
    write.submit()
    write.next_card()
    assert not write.awaiting_next
    assert write.progress_text() == "2 / 2"


def test_write_summary_counts(write) -> None:
    _type(write, "париж")
    write.submit()
    write.next_card()
    _type(write, "неверно")
    write.submit()
    write.next_card()
    assert write.is_finished
    assert "1 из 2" in write.summary_text()


def test_write_records_progress(conn, qt_host) -> None:
    progress = SqliteProgressRepository(conn)
    decks = SqliteDeckRepository(conn)
    library = LibraryService(decks)
    deck = library.import_tsv("Франция\tПариж", "Гео")
    card = deck.cards[0]

    view = WriteView(StudyService(progress), parent=qt_host)
    view.start(deck.cards, shuffle=False)
    view.findChild(object, "answerEdit").setText("париж")
    view.submit()
    view.next_card()

    saved = progress.get(card.id)
    assert saved is not None
    assert saved.repetitions == 1
    assert progress.reviews_for(card.id)[0].mode == "write"


def test_write_records_after_override(conn, qt_host) -> None:
    """Оспоренный ответ должен попасть в историю уже как верный."""
    progress = SqliteProgressRepository(conn)
    library = LibraryService(SqliteDeckRepository(conn))
    deck = library.import_tsv("Франция\tПариж", "Гео")
    card = deck.cards[0]

    view = WriteView(StudyService(progress), parent=qt_host)
    view.start(deck.cards, shuffle=False)
    view.findChild(object, "answerEdit").setText("Лондон")
    view.submit()
    view.override()
    view.next_card()

    review = progress.reviews_for(card.id)[0]
    assert review.is_correct is True
    assert len(progress.reviews_for(card.id)) == 1  # ровно одна запись, не две


def test_write_skips_non_text_answers(qt_host) -> None:
    latex_card = Card.create(
        CardFace.from_text("производная"), CardFace((LatexBlock(r"\cos x"),))
    )
    view = WriteView(parent=qt_host)
    view.start([CARDS[0], latex_card], shuffle=False)
    assert view.progress_text() == "1 / 1"
