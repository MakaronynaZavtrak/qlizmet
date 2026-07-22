"""Тесты экрана правки набора и диалога карточки."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from qlizmet.app.deck_service import DeckService  # noqa: E402
from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.core.models import Card, CardFace, LatexBlock  # noqa: E402
from qlizmet.storage.sqlite.repositories import SqliteDeckRepository  # noqa: E402
from qlizmet.ui.views.card_editor_dialog import CardEditorDialog  # noqa: E402
from qlizmet.ui.views.deck_editor_view import DeckEditorView  # noqa: E402


@pytest.fixture
def services(conn):
    repo = SqliteDeckRepository(conn)
    return LibraryService(repo), DeckService(repo)


@pytest.fixture
def editor(services, qt_host) -> DeckEditorView:
    library, decks = services
    deck = library.create("Гео")
    view = DeckEditorView(decks, parent=qt_host)
    view.load(deck.id)
    return view


# --- экран набора ---


def test_empty_deck_shows_hint(editor) -> None:
    assert editor.card_ids() == []
    assert editor.findChild(object, "emptyHint") is not None


def test_title_is_shown(editor) -> None:
    assert editor.findChild(object, "deckTitle").text() == "Гео"


def test_add_card_appears_in_list(editor) -> None:
    card_id = editor.add_card_from_markup("Франция", "Париж")
    assert editor.card_ids() == [card_id]
    assert editor.selected_card_id() == card_id


def test_list_row_shows_both_sides(editor) -> None:
    editor.add_card_from_markup("Франция", "Париж")
    text = editor.findChild(object, "cardList").item(0).text()
    assert "Франция" in text
    assert "Париж" in text


def test_formula_card_row_is_marked(editor) -> None:
    editor.add_card_from_markup("производная sin x", r"$\cos x$")
    text = editor.findChild(object, "cardList").item(0).text()
    assert "формула" in text


def test_update_card_changes_row(editor) -> None:
    card_id = editor.add_card_from_markup("Франция", "Лондон")
    editor.update_card(card_id, CardFace.from_text("Франция"), CardFace.from_text("Париж"))
    assert "Париж" in editor.findChild(object, "cardList").item(0).text()


def test_delete_card(editor) -> None:
    card_id = editor.add_card_from_markup("Франция", "Париж")
    assert editor.delete_card(card_id) is True
    assert editor.card_ids() == []


def test_move_selected_reorders(editor) -> None:
    first = editor.add_card_from_markup("Франция", "Париж")
    second = editor.add_card_from_markup("Италия", "Рим")

    editor.select_card(first)
    assert editor.move_selected(+1) is True
    assert editor.card_ids() == [second, first]
    assert editor.selected_card_id() == first


def test_move_at_edge_is_refused(editor) -> None:
    card_id = editor.add_card_from_markup("Франция", "Париж")
    editor.select_card(card_id)
    assert editor.move_selected(-1) is False


def test_move_without_selection(editor) -> None:
    assert editor.move_selected(+1) is False


def test_back_button_emits_signal(editor) -> None:
    seen: list[bool] = []
    editor.back_requested.connect(lambda: seen.append(True))
    editor.findChild(object, "backButton").click()
    assert seen == [True]


def test_editing_without_loaded_deck_raises(services, qt_host) -> None:
    _, decks = services
    view = DeckEditorView(decks, parent=qt_host)
    with pytest.raises(RuntimeError):
        view.add_card_from_markup("a", "b")


# --- диалог карточки ---


def test_dialog_parses_markup(qt_host) -> None:
    dialog = CardEditorDialog(parent=qt_host)
    dialog.set_markup(front="производная $\\sin x$", back="cos x", tags="матан, важное")

    assert isinstance(dialog.front_face().blocks[1], LatexBlock)
    assert dialog.back_face().plain_text == "cos x"
    assert dialog.tags() == ("матан", "важное")


def test_dialog_loads_existing_card(qt_host) -> None:
    card = Card.create(
        CardFace.from_text("Франция"), CardFace((LatexBlock(r"\cos x"),)), ("гео",)
    )
    dialog = CardEditorDialog(card, parent=qt_host)

    assert dialog.findChild(object, "frontEdit").toPlainText() == "Франция"
    assert dialog.findChild(object, "backEdit").toPlainText() == "$\\cos x$"
    assert dialog.tags() == ("гео",)


def test_dialog_preview_updates_live(qt_host) -> None:
    dialog = CardEditorDialog(parent=qt_host)
    dialog.set_markup(front=r"$\frac{1}{2}$")

    preview = dialog.findChild(object, "frontPreview")
    names = [w.objectName() for w in preview.block_widgets()]
    assert names == ["faceBlockLatex"]


def test_dialog_reports_empty(qt_host) -> None:
    dialog = CardEditorDialog(parent=qt_host)
    assert dialog.is_empty()
    dialog.set_markup(front="Франция")
    assert not dialog.is_empty()


def test_dialog_ignores_blank_tags(qt_host) -> None:
    dialog = CardEditorDialog(parent=qt_host)
    dialog.set_markup(tags=" , ,гео,  ")
    assert dialog.tags() == ("гео",)