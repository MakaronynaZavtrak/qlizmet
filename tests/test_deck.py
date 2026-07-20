"""Тесты набора карточек."""
from datetime import datetime, timedelta, timezone

from qlizmet.core.models import Card, CardFace, Deck


def _card(front: str, back: str) -> Card:
    return Card.create(CardFace.from_text(front), CardFace.from_text(back))


def test_empty_deck() -> None:
    deck = Deck.create("Пустой")
    assert len(deck) == 0
    assert list(deck) == []


def test_add_card_grows_and_touches() -> None:
    created = datetime(2026, 1, 1, tzinfo=timezone.utc)
    later = created + timedelta(hours=1)
    deck = Deck.create("Гео", now=created)
    deck.add_card(_card("Франция", "Париж"), now=later)
    assert len(deck) == 1
    assert deck.modified_at == later


def test_get_card_finds_and_misses() -> None:
    deck = Deck.create("Гео")
    card = _card("Италия", "Рим")
    deck.add_card(card)
    assert deck.get_card(card.id) is card
    assert deck.get_card("нет-такого") is None


def test_remove_card_reports_success() -> None:
    deck = Deck.create("Гео")
    card = _card("Испания", "Мадрид")
    deck.add_card(card)
    assert deck.remove_card(card.id) is True
    assert len(deck) == 0
    assert deck.remove_card(card.id) is False