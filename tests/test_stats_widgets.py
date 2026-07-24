"""Тесты плитки показателя и составной полосы."""
import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QPainter, QPixmap  # noqa: E402

from qlizmet.ui.widgets.metric_tile import MetricTile  # noqa: E402
from qlizmet.ui.widgets.segmented_bar import Segment, SegmentedBar  # noqa: E402


# --- плитка ---


def test_tile_starts_empty(qt_host) -> None:
    tile = MetricTile("Всего", value_name="totalValue", parent=qt_host)
    assert tile.value_text() == "—"
    assert tile.caption_text() == "Всего"


def test_tile_shows_value(qt_host) -> None:
    tile = MetricTile("Всего", value_name="totalValue", parent=qt_host)
    tile.set_value("42")
    assert tile.value_text() == "42"


def test_tile_value_is_findable_by_name(qt_host) -> None:
    """Значение доступно по objectName — на это опираются тесты экрана."""
    tile = MetricTile("Новых", value_name="newValue", parent=qt_host)
    tile.set_value("7")
    assert tile.findChild(object, "newValue").text() == "7"


def test_accent_tile_has_its_own_style_name(qt_host) -> None:
    plain = MetricTile("Всего", value_name="a", parent=qt_host)
    accent = MetricTile("Пора повторить", value_name="b", accent=True, parent=qt_host)
    assert plain.objectName() != accent.objectName()


# --- полоса ---


def test_bar_starts_empty(qt_host) -> None:
    bar = SegmentedBar(parent=qt_host)
    assert bar.segments() == ()
    assert bar.total == 0


def test_bar_keeps_segments(qt_host) -> None:
    bar = SegmentedBar(parent=qt_host)
    bar.set_segments(
        [Segment(3, "#1d9e75", "закреплено"), Segment(2, "#25b98a", "в работе")],
        empty_color="#262a32",
    )
    assert bar.total == 5
    assert len(bar.segments()) == 2


def test_bar_drops_empty_segments(qt_host) -> None:
    """Нулевые доли не должны попадать в полосу — иначе рисуем пустоту."""
    bar = SegmentedBar(parent=qt_host)
    bar.set_segments(
        [Segment(3, "#1d9e75"), Segment(0, "#25b98a"), Segment(1, "#9aa1ad")],
        empty_color="#262a32",
    )
    assert len(bar.segments()) == 2
    assert bar.total == 4


def test_painting_empty_bar_does_not_crash(qt_host) -> None:
    bar = SegmentedBar(parent=qt_host)
    bar.resize(200, 14)
    pixmap = QPixmap(200, 14)
    pixmap.fill()
    painter = QPainter(pixmap)
    painter.end()
    bar.render(pixmap)  # не должно падать при нулевом итоге


def test_painting_filled_bar_does_not_crash(qt_host) -> None:
    bar = SegmentedBar(parent=qt_host)
    bar.resize(200, 14)
    bar.set_segments(
        [Segment(1, "#1d9e75"), Segment(2, "#25b98a")], empty_color="#262a32"
    )
    pixmap = QPixmap(200, 14)
    pixmap.fill()
    bar.render(pixmap)
