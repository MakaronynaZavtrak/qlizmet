"""Тесты репозитория наборов на SQLite."""
from datetime import datetime, timezone

from qlizmet.core.models import Card, CardFace, CardProgress, Deck, LatexBlock, TextBlock
from qlizmet.storage.sqlite.repositories import (
    SqliteDeckRepository,
    SqliteProgressRepository,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _card(front: str, back: str) -> Card:
    return Card.create(CardFace.from_text(front), CardFace.from_text(back), now=NOW)


def _deck_with_cards() -> Deck:
    deck = Deck.create("Гео", "столицы", now=NOW)
    deck.add_card(_card("Франция", "Париж"), now=NOW)
    deck.add_card(_card("Италия", "Рим"), now=NOW)
    return deck


def test_save_and_get_roundtrip(conn) -> None:
    repo = SqliteDeckRepository(conn)
    deck = _deck_with_cards()
    repo.save(deck)

    loaded = repo.get(deck.id)
    assert loaded is not None
    assert loaded.title == "Гео"
    assert loaded.description == "столицы"
    assert len(loaded) == 2


def test_card_order_is_preserved(conn) -> None:
    repo = SqliteDeckRepository(conn)
    deck = _deck_with_cards()
    repo.save(deck)

    loaded = repo.get(deck.id)
    assert [c.front.plain_text for c in loaded.cards] == ["Франция", "Италия"]


def test_rich_content_roundtrip(conn) -> None:
    repo = SqliteDeckRepository(conn)
    deck = Deck.create("Матан", now=NOW)
    deck.add_card(
        Card.create(
            CardFace((TextBlock("производная "), LatexBlock(r"\sin x"))),
            CardFace.from_text("cos x"),
            now=NOW,
        ),
        now=NOW,
    )
    repo.save(deck)

    loaded = repo.get(deck.id)
    front_blocks = loaded.cards[0].front.blocks
    assert isinstance(front_blocks[0], TextBlock)
    assert isinstance(front_blocks[1], LatexBlock)


def test_get_missing_returns_none(conn) -> None:
    assert SqliteDeckRepository(conn).get("нет-такого") is None


def test_list_deck_ids(conn) -> None:
    repo = SqliteDeckRepository(conn)
    repo.save(Deck.create("Alpha", now=NOW))
    repo.save(Deck.create("Beta", now=NOW))
    assert len(repo.list_deck_ids()) == 2


def test_delete_reports_success_then_gone(conn) -> None:
    repo = SqliteDeckRepository(conn)
    deck = _deck_with_cards()
    repo.save(deck)

    assert repo.delete(deck.id) is True
    assert repo.get(deck.id) is None
    assert repo.delete(deck.id) is False


def test_resave_updates_title_and_removes_dropped_card(conn) -> None:
    repo = SqliteDeckRepository(conn)
    deck = _deck_with_cards()
    repo.save(deck)

    deck.title = "География"
    deck.remove_card(deck.cards[0].id, now=NOW)
    repo.save(deck)

    loaded = repo.get(deck.id)
    assert loaded.title == "География"
    assert len(loaded) == 1
    assert loaded.cards[0].front.plain_text == "Италия"


def test_resave_preserves_progress_of_surviving_cards(conn) -> None:
    decks = SqliteDeckRepository(conn)
    progress = SqliteProgressRepository(conn)
    deck = _deck_with_cards()
    decks.save(deck)

    kept = deck.cards[1]
    progress.save(CardProgress(kept.id, ease=2.3, interval_days=6, repetitions=2))

    # редактируем набор и пересохраняем — прогресс уцелевшей карточки не должен пропасть
    deck.title = "Новое имя"
    decks.save(deck)

    loaded_progress = progress.get(kept.id)
    assert loaded_progress is not None
    assert loaded_progress.interval_days == 6