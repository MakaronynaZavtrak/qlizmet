"""Тесты сервиса редактирования карточек набора."""
import pytest

from qlizmet.app.deck_service import DeckService
from qlizmet.app.library_service import LibraryService
from qlizmet.core.models import CardFace, CardProgress, LatexBlock
from qlizmet.storage.sqlite.repositories import (
    SqliteDeckRepository,
    SqliteProgressRepository,
)


@pytest.fixture
def services(conn):
    repo = SqliteDeckRepository(conn)
    return LibraryService(repo), DeckService(repo)


def _face(text: str) -> CardFace:
    return CardFace.from_text(text)


def test_add_card(services) -> None:
    library, decks = services
    deck = library.create("Гео")
    card = decks.add_card(deck.id, _face("Франция"), _face("Париж"))

    stored = decks.get(deck.id)
    assert len(stored) == 1
    assert stored.cards[0].id == card.id
    assert stored.cards[0].back.plain_text == "Париж"


def test_add_card_with_formula(services) -> None:
    library, decks = services
    deck = library.create("Матан")
    decks.add_card(deck.id, _face("производная sin x"), CardFace((LatexBlock(r"\cos x"),)))

    stored = decks.get(deck.id)
    assert isinstance(stored.cards[0].back.blocks[0], LatexBlock)


def test_add_card_with_tags(services) -> None:
    library, decks = services
    deck = library.create("Гео")
    decks.add_card(deck.id, _face("Франция"), _face("Париж"), ("европа",))
    assert decks.get(deck.id).cards[0].tags == ("европа",)


def test_empty_card_rejected(services) -> None:
    library, decks = services
    deck = library.create("Гео")
    with pytest.raises(ValueError):
        decks.add_card(deck.id, CardFace(), CardFace())


def test_add_to_missing_deck_raises(services) -> None:
    _, decks = services
    with pytest.raises(LookupError):
        decks.add_card("нет-такого", _face("a"), _face("b"))


def test_update_card(services) -> None:
    library, decks = services
    deck = library.create("Гео")
    card = decks.add_card(deck.id, _face("Франция"), _face("Лондон"))

    decks.update_card(deck.id, card.id, _face("Франция"), _face("Париж"))
    assert decks.get(deck.id).cards[0].back.plain_text == "Париж"


def test_update_missing_card_raises(services) -> None:
    library, decks = services
    deck = library.create("Гео")
    with pytest.raises(LookupError):
        decks.update_card(deck.id, "нет-такой", _face("a"), _face("b"))


def test_update_preserves_progress(services, conn) -> None:
    """Правка текста карточки не должна стирать её прогресс."""
    library, decks = services
    deck = library.create("Гео")
    card = decks.add_card(deck.id, _face("Франция"), _face("Париж"))

    progress = SqliteProgressRepository(conn)
    progress.save(CardProgress(card.id, ease=2.4, interval_days=6, repetitions=2))

    decks.update_card(deck.id, card.id, _face("Франция"), _face("Париж (столица)"))

    saved = progress.get(card.id)
    assert saved is not None
    assert saved.interval_days == 6


def test_delete_card(services) -> None:
    library, decks = services
    deck = library.create("Гео")
    card = decks.add_card(deck.id, _face("Франция"), _face("Париж"))

    assert decks.delete_card(deck.id, card.id) is True
    assert len(decks.get(deck.id)) == 0
    assert decks.delete_card(deck.id, card.id) is False


def test_move_card_down_and_up(services) -> None:
    library, decks = services
    deck = library.create("Гео")
    first = decks.add_card(deck.id, _face("Франция"), _face("Париж"))
    second = decks.add_card(deck.id, _face("Италия"), _face("Рим"))

    assert decks.move_card(deck.id, first.id, +1) is True
    assert [c.id for c in decks.get(deck.id).cards] == [second.id, first.id]

    assert decks.move_card(deck.id, first.id, -1) is True
    assert [c.id for c in decks.get(deck.id).cards] == [first.id, second.id]


def test_move_beyond_edges_is_refused(services) -> None:
    library, decks = services
    deck = library.create("Гео")
    card = decks.add_card(deck.id, _face("Франция"), _face("Париж"))

    assert decks.move_card(deck.id, card.id, -1) is False
    assert decks.move_card(deck.id, card.id, +1) is False


def test_move_missing_card(services) -> None:
    library, decks = services
    deck = library.create("Гео")
    assert decks.move_card(deck.id, "нет-такой", 1) is False