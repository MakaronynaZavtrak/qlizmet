"""Тесты карточки."""
from datetime import datetime, timedelta, timezone

from qlizmet.core.models import Card, CardFace


def _face(text: str) -> CardFace:
    return CardFace.from_text(text)


def test_create_sets_id_and_equal_timestamps() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    card = Card.create(_face("вопрос"), _face("ответ"), now=now)
    assert card.id
    assert card.created_at == now
    assert card.modified_at == now


def test_each_card_gets_unique_id() -> None:
    a = Card.create(_face("a"), _face("1"))
    b = Card.create(_face("b"), _face("2"))
    assert a.id != b.id


def test_tags_are_stored() -> None:
    card = Card.create(_face("q"), _face("a"), tags=("гео", "столицы"))
    assert card.tags == ("гео", "столицы")


def test_touch_updates_only_modified_at() -> None:
    created = datetime(2026, 1, 1, tzinfo=timezone.utc)
    later = created + timedelta(days=3)
    card = Card.create(_face("q"), _face("a"), now=created)
    card.touch(now=later)
    assert card.created_at == created
    assert card.modified_at == later