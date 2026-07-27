"""Формула-карточка показывается в списке набора картинкой, а не сырым LaTeX."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from PySide6.QtCore import QRect, Qt  # noqa: E402
from PySide6.QtGui import QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QListWidget,
    QListWidgetItem,
    QStyleOptionViewItem,
)

from qlizmet.app.deck_service import DeckService  # noqa: E402
from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.core.models import CardFace, LatexBlock  # noqa: E402
from qlizmet.storage.sqlite.repositories import SqliteDeckRepository  # noqa: E402
from qlizmet.ui.views.deck_editor_view import DeckEditorView  # noqa: E402
from qlizmet.ui.widgets.list_delegate import (  # noqa: E402
    SUBTITLE_LATEX_ROLE,
    SUBTITLE_ROLE,
    TITLE_LATEX_ROLE,
    TwoLineDelegate,
)


@pytest.fixture
def editor(conn, qt_host) -> DeckEditorView:
    repo = SqliteDeckRepository(conn)
    library, decks = LibraryService(repo), DeckService(repo)
    deck = library.create("Матан")
    view = DeckEditorView(decks, parent=qt_host)
    view.load(deck.id)
    return view


def _item(editor: DeckEditorView, index: int = 0) -> QListWidgetItem:
    return editor.findChild(object, "cardList").item(index)


def test_formula_front_sets_title_latex_role(editor) -> None:
    editor.add_card(CardFace((LatexBlock(r"\frac{1}{2}"),)), CardFace.from_text("половина"))
    item = _item(editor)
    assert item.data(TITLE_LATEX_ROLE) == r"\frac{1}{2}"
    assert item.data(SUBTITLE_LATEX_ROLE) is None  # оборот — обычный текст


def test_formula_back_sets_subtitle_latex_role(editor) -> None:
    editor.add_card(CardFace.from_text("половина"), CardFace((LatexBlock(r"\frac{1}{2}"),)))
    item = _item(editor)
    assert item.data(SUBTITLE_LATEX_ROLE) == r"\frac{1}{2}"
    assert item.data(TITLE_LATEX_ROLE) is None


def test_plain_text_card_has_no_latex_role(editor) -> None:
    editor.add_card_from_markup("Франция", "Париж")
    item = _item(editor)
    assert item.data(TITLE_LATEX_ROLE) is None
    assert item.data(SUBTITLE_LATEX_ROLE) is None


def test_mixed_text_and_formula_stays_text(editor) -> None:
    """Грань «текст + формула» не одна формула — картинкой не показываем."""
    editor.add_card_from_markup("Значение $x$ равно", "два")
    item = _item(editor)
    assert item.data(TITLE_LATEX_ROLE) is None  # смешанная грань остаётся текстом


def test_delegate_renders_formula_as_pixmap(qt_host) -> None:
    listing = QListWidget(parent=qt_host)
    delegate = TwoLineDelegate(listing)
    listing.setItemDelegate(delegate)
    item = QListWidgetItem("[формула]")
    item.setData(SUBTITLE_ROLE, "половина")
    item.setData(TITLE_LATEX_ROLE, r"\frac{1}{2}")
    listing.addItem(item)

    # формула валидная -> картинка получилась
    pixmap = delegate._formula_pixmap(r"\frac{1}{2}", "#e6e8ec", 20)
    assert pixmap is not None and not pixmap.isNull()

    # и отрисовка строки-формулы проходит без ошибок
    option = QStyleOptionViewItem()
    option.initFrom(listing)
    option.rect = QRect(0, 0, 300, 60)
    option.font = listing.font()
    option.fontMetrics = listing.fontMetrics()
    canvas = QPixmap(300, 60)
    canvas.fill()
    painter = QPainter(canvas)
    try:
        delegate.paint(painter, option, listing.model().index(0, 0))
    finally:
        painter.end()
