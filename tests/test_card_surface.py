"""Тесты карточки-контейнера и её переворота."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from PySide6.QtWidgets import QLabel  # noqa: E402

from qlizmet.core.models import Card, CardFace  # noqa: E402
from qlizmet.ui.views.flashcards_view import FlashcardsView  # noqa: E402
from qlizmet.ui.widgets.card_surface import FLIP_MS, CardSurface  # noqa: E402


def _card(front: str, back: str) -> Card:
    return Card.create(CardFace.from_text(front), CardFace.from_text(back))


CARDS = [_card("Франция", "Париж"), _card("Италия", "Рим")]


# --- сама карточка ---


def test_content_is_placed_inside(qt_host) -> None:
    label = QLabel("содержимое")
    surface = CardSurface(label, animated=False, parent=qt_host)
    assert label.parent() is surface


def test_object_name_is_styled_by_theme(qt_host) -> None:
    surface = CardSurface(QLabel(), animated=False, parent=qt_host)
    assert surface.objectName() == "cardSurface"


def test_flip_without_animation_swaps_immediately(qt_host) -> None:
    surface = CardSurface(QLabel(), animated=False, parent=qt_host)
    calls: list[str] = []
    surface.flip(lambda: calls.append("swapped"))
    assert calls == ["swapped"]
    assert not surface.is_animating


def test_flip_without_animation_emits_signal(qt_host) -> None:
    surface = CardSurface(QLabel(), animated=False, parent=qt_host)
    done: list[bool] = []
    surface.flip_finished.connect(lambda: done.append(True))
    surface.flip(lambda: None)
    assert done == [True]


def _flipping_card(qt_host) -> CardSurface:
    """Карточка нормальной ширины, готовая к перевороту."""
    surface = CardSurface(QLabel("Франция"), animated=True, parent=qt_host)
    surface.resize(600, 300)
    return surface


def test_flip_produces_many_intermediate_frames(qt_host) -> None:
    """Переворот должен идти плавно, а не подменять кадр целиком."""
    surface = _flipping_card(qt_host)
    surface.flip(lambda: None)
    animation = surface.animation

    widths = []
    for step in range(0, 11):
        animation.setCurrentTime(int(FLIP_MS * step / 10))
        widths.append(surface.maximumWidth())

    # промежуточных значений должно быть много, а не два
    assert len(set(widths)) >= 6
    # и карточка должна сначала сжаться почти в ноль
    assert min(widths) < 10


def test_flip_narrows_then_widens(qt_host) -> None:
    surface = _flipping_card(qt_host)
    surface.flip(lambda: None)
    animation = surface.animation

    animation.setCurrentTime(FLIP_MS // 4)
    quarter = surface.maximumWidth()
    animation.setCurrentTime(FLIP_MS // 2)
    middle = surface.maximumWidth()
    animation.setCurrentTime(FLIP_MS * 3 // 4)
    three_quarters = surface.maximumWidth()

    assert middle < quarter
    assert middle < three_quarters


def test_content_swaps_exactly_at_midpoint(qt_host) -> None:
    surface = _flipping_card(qt_host)
    swaps: list[str] = []
    surface.flip(lambda: swaps.append("swapped"))
    animation = surface.animation

    animation.setCurrentTime(FLIP_MS // 4)
    assert swaps == []          # ещё лицо

    animation.setCurrentTime(FLIP_MS // 2)
    assert swaps == ["swapped"]  # на ребре подменили

    animation.setCurrentTime(FLIP_MS)
    assert swaps == ["swapped"]  # и только один раз


def test_interrupted_flip_still_swaps(qt_host) -> None:
    """Прерванный переворот не должен потерять подмену стороны."""
    surface = _flipping_card(qt_host)
    swaps: list[str] = []
    surface.flip(lambda: swaps.append("swapped"))
    surface.animation.setCurrentTime(FLIP_MS // 4)
    surface.stop_animation()

    assert swaps == ["swapped"]
    assert surface.minimumWidth() > 0  # ограничения вернулись на место


def test_animated_flip_starts_animation(qt_host) -> None:
    """С анимацией подмена содержимого откладывается до её середины."""
    surface = CardSurface(QLabel(), animated=True, parent=qt_host)
    surface.resize(400, 200)
    calls: list[str] = []
    surface.flip(lambda: calls.append("swapped"))

    assert surface.is_animating
    assert calls == []  # ещё не подменили — карточка только начала складываться
    surface.stop_animation()


def test_stop_animation_restores_width(qt_host) -> None:
    surface = CardSurface(QLabel(), animated=True, parent=qt_host)
    surface.resize(400, 200)
    surface.flip(lambda: None)
    surface.stop_animation()

    assert not surface.is_animating
    assert surface.maximumWidth() > 400


def test_repeated_flip_does_not_pile_up(qt_host) -> None:
    surface = CardSurface(QLabel(), animated=True, parent=qt_host)
    surface.resize(400, 200)
    surface.flip(lambda: None)
    surface.flip(lambda: None)  # второй раз до конца первого — не должно ломаться
    assert surface.is_animating
    surface.stop_animation()


# --- экран «Карточки» ---


def test_screen_uses_card_surface(qt_host) -> None:
    view = FlashcardsView(animated=False, parent=qt_host)
    assert view.findChild(CardSurface) is not None


def test_state_changes_even_while_animating(qt_host) -> None:
    """Логика не должна ждать анимацию: ответ считается показанным сразу."""
    view = FlashcardsView(animated=True, parent=qt_host)
    view.start(CARDS, shuffle=False)
    view.flip()
    assert view.answer_shown
    view.findChild(CardSurface).stop_animation()


def test_marking_stops_animation(qt_host) -> None:
    view = FlashcardsView(animated=True, parent=qt_host)
    view.start(CARDS, shuffle=False)
    view.flip()
    view.mark(known=True)
    assert not view.findChild(CardSurface).is_animating
    assert not view.answer_shown
