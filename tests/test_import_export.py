"""Тесты импорта и экспорта TSV."""
from datetime import datetime, timezone

from qlizmet.core.models import Card, CardFace, Deck
from qlizmet.storage.import_export.tsv import export_deck_to_tsv, import_deck_from_tsv

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_export_produces_tab_separated_lines() -> None:
    deck = Deck.create("Гео", now=NOW)
    deck.add_card(
        Card.create(CardFace.from_text("Франция"), CardFace.from_text("Париж"), now=NOW),
        now=NOW,
    )
    assert export_deck_to_tsv(deck) == "Франция\tПариж"


def test_import_skips_blank_and_untabbed_lines() -> None:
    text = "Франция\tПариж\n\nмусор без таба\nИталия\tРим\n"
    deck = import_deck_from_tsv(text, "Гео", now=NOW)
    assert len(deck) == 2


def test_roundtrip_preserves_plain_text() -> None:
    original = import_deck_from_tsv("Франция\tПариж\nИталия\tРим", "Гео", now=NOW)
    restored = import_deck_from_tsv(export_deck_to_tsv(original), "Гео", now=NOW)

    assert [(c.front.plain_text, c.back.plain_text) for c in restored.cards] == [
        ("Франция", "Париж"),
        ("Италия", "Рим"),
    ]