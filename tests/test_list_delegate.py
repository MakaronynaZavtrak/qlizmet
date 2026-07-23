"""Тесты двухстрочного элемента списка."""
import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QModelIndex, QRect, QSize, Qt  # noqa: E402
from PySide6.QtGui import QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QStyleOptionViewItem  # noqa: E402

from qlizmet.ui.widgets.list_delegate import SUBTITLE_ROLE, TwoLineDelegate  # noqa: E402


@pytest.fixture
def listing(qt_host) -> QListWidget:
    widget = QListWidget(parent=qt_host)
    widget.setItemDelegate(TwoLineDelegate(widget))
    return widget


def _add(listing: QListWidget, title: str, subtitle: str | None) -> QListWidgetItem:
    item = QListWidgetItem(title)
    if subtitle is not None:
        item.setData(SUBTITLE_ROLE, subtitle)
    listing.addItem(item)
    return item


def _option(listing: QListWidget) -> QStyleOptionViewItem:
    option = QStyleOptionViewItem()
    option.initFrom(listing)
    option.rect = QRect(0, 0, 300, 60)
    option.font = listing.font()
    option.fontMetrics = listing.fontMetrics()
    return option


def test_subtitle_is_stored_separately(listing) -> None:
    item = _add(listing, "Гео", "2 карт.")
    assert item.text() == "Гео"
    assert item.data(SUBTITLE_ROLE) == "2 карт."


def test_two_line_item_is_taller(listing) -> None:
    with_subtitle = _add(listing, "Гео", "2 карт.")
    plain = _add(listing, "Просто строка", None)
    delegate = listing.itemDelegate()
    option = _option(listing)

    tall = delegate.sizeHint(option, listing.indexFromItem(with_subtitle))
    short = delegate.sizeHint(option, listing.indexFromItem(plain))
    assert tall.height() > short.height()


def test_painting_does_not_crash(listing) -> None:
    """Отрисовка обеих веток (с подзаголовком и без) должна проходить без ошибок."""
    _add(listing, "Гео", "2 карт.")
    _add(listing, "Без подзаголовка", None)
    delegate = listing.itemDelegate()

    pixmap = QPixmap(300, 120)
    pixmap.fill()
    painter = QPainter(pixmap)
    try:
        for row in range(listing.count()):
            delegate.paint(painter, _option(listing), listing.model().index(row, 0))
    finally:
        painter.end()


def test_long_text_is_elided(listing) -> None:
    """Длинный текст не должен вылезать за пределы строки."""
    item = _add(listing, "очень длинный термин " * 10, "и длинное определение " * 10)
    delegate = listing.itemDelegate()
    size = delegate.sizeHint(_option(listing), listing.indexFromItem(item))
    assert size.height() < 200
