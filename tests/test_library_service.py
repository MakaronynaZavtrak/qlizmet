"""Тесты сервиса библиотеки наборов и сводки по наборам."""
import pytest

from qlizmet.app.library_service import LibraryService
from qlizmet.core.models import Card, CardFace
from qlizmet.storage.sqlite.repositories import SqliteDeckRepository


@pytest.fixture
def library(conn) -> LibraryService:
    return LibraryService(SqliteDeckRepository(conn))


def test_empty_library(library) -> None:
    assert library.summaries() == []


def test_create_and_list(library) -> None:
    library.create("Гео", "столицы")
    summaries = library.summaries()
    assert len(summaries) == 1
    assert summaries[0].title == "Гео"
    assert summaries[0].description == "столицы"
    assert summaries[0].card_count == 0


def test_summaries_count_cards(library, conn) -> None:
    deck = library.create("Гео")
    deck.add_card(Card.create(CardFace.from_text("Франция"), CardFace.from_text("Париж")))
    SqliteDeckRepository(conn).save(deck)

    assert library.summaries()[0].card_count == 1


def test_summaries_sorted_by_title(library) -> None:
    library.create("Ямал")
    library.create("Абакан")
    assert [s.title for s in library.summaries()] == ["Абакан", "Ямал"]


def test_blank_title_rejected(library) -> None:
    with pytest.raises(ValueError):
        library.create("   ")


def test_title_is_trimmed(library) -> None:
    library.create("  Гео  ")
    assert library.summaries()[0].title == "Гео"


def test_rename(library) -> None:
    deck = library.create("Старое")
    library.rename(deck.id, "Новое", "описание")
    summary = library.summaries()[0]
    assert summary.title == "Новое"
    assert summary.description == "описание"


def test_rename_missing_deck_raises(library) -> None:
    with pytest.raises(LookupError):
        library.rename("нет-такого", "Имя")


def test_delete(library) -> None:
    deck = library.create("Гео")
    assert library.delete(deck.id) is True
    assert library.summaries() == []
    assert library.delete(deck.id) is False


def test_import_tsv(library) -> None:
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")
    assert library.summaries()[0].card_count == 2
    assert library.get(deck.id).cards[0].front.plain_text == "Франция"


def test_export_tsv_roundtrip(library) -> None:
    deck = library.import_tsv("Франция\tПариж", "Гео")
    assert library.export_tsv(deck.id) == "Франция\tПариж"