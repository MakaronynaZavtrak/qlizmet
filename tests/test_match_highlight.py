"""Подсветка в «Подборе пар»: зелёная вспышка на совпадении, красная на промахе.

Состояние подсветки ставится синхронно (до гасящего таймера), поэтому проверяется
без ожидания: убеждаемся, что плитки получают нужное состояние, а уходящая пара
становится некликабельной ещё до удаления с поля.
"""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from qlizmet.core.models import Card, CardFace  # noqa: E402
from qlizmet.ui.views.match_view import (  # noqa: E402
    STATE_MATCH,
    STATE_WRONG,
    MatchView,
)

CARDS = [
    Card.create(CardFace.from_text("Франция"), CardFace.from_text("Париж")),
    Card.create(CardFace.from_text("Италия"), CardFace.from_text("Рим")),
    Card.create(CardFace.from_text("Испания"), CardFace.from_text("Мадрид")),
]


def _view(qt_host) -> MatchView:
    view = MatchView(parent=qt_host)
    view.start(CARDS, autostart=False)
    return view


def _pair(card: Card) -> tuple[str, str]:
    return f"{card.id}:front", f"{card.id}:back"


def test_match_flashes_green_and_locks_pair(qt_host) -> None:
    view = _view(qt_host)
    front, back = _pair(CARDS[0])  # не последняя пара из трёх
    view.select_tile(front)
    view.select_tile(back)
    for tile_id in (front, back):
        button = view._buttons[tile_id]
        assert button.property("state") == STATE_MATCH
        assert not button.isEnabled()  # уходящую плитку больше не нажать


def test_mismatch_flashes_red_on_both(qt_host) -> None:
    view = _view(qt_host)
    front, _ = _pair(CARDS[0])
    _, other_back = _pair(CARDS[1])
    view.select_tile(front)
    view.select_tile(other_back)
    for tile_id in (front, other_back):
        assert view._buttons[tile_id].property("state") == STATE_WRONG


def test_final_pair_shows_summary_without_flash(qt_host) -> None:
    """Последняя пара сразу открывает итог (вспышку не ждём)."""
    view = _view(qt_host)
    for card in CARDS:
        front, back = _pair(card)
        view.select_tile(front)
        view.select_tile(back)
    assert view.is_finished
    assert "Готово" in view.summary_text()
