"""Тесты карточек режимов на экране выбора."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from qlizmet.app.deck_service import DeckService  # noqa: E402
from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.core.models import CardFace, LatexBlock  # noqa: E402
from qlizmet.core.study import StudyMode  # noqa: E402
from qlizmet.storage.sqlite.repositories import SqliteDeckRepository  # noqa: E402
from qlizmet.ui.theme import Theme, apply_theme  # noqa: E402
from qlizmet.ui.views.mode_select_view import MODE_ICONS, ModeSelectView  # noqa: E402
from qlizmet.ui.widgets.mode_card import ModeCard  # noqa: E402


@pytest.fixture
def services(conn):
    repo = SqliteDeckRepository(conn)
    return LibraryService(repo), DeckService(repo)


@pytest.fixture
def view(services, qt_host) -> ModeSelectView:
    library, decks = services
    deck = library.import_tsv("Франция\tПариж\nИталия\tРим", "Гео")
    screen = ModeSelectView(decks, parent=qt_host)
    screen.load(deck.id)
    return screen


# --- сама карточка ---


def test_card_behaves_like_a_button(qt_host) -> None:
    """Карточка должна оставаться кнопкой: клик, фокус, клавиатура."""
    card = ModeCard("Карточки", icon_name="cards", parent=qt_host)
    clicks: list[bool] = []
    card.clicked.connect(lambda: clicks.append(True))
    card.click()
    assert clicks == [True]
    assert card.focusPolicy() != 0


def test_card_shows_title_and_hint(qt_host) -> None:
    card = ModeCard("Письмо", icon_name="pencil", parent=qt_host)
    card.set_hint("Печатай ответ")
    assert card.title_text() == "Письмо"
    assert card.hint_text() == "Печатай ответ"


def test_unavailable_card_shows_reason_instead_of_description(qt_host) -> None:
    card = ModeCard("Подбор пар", icon_name="grid", parent=qt_host)
    card.set_available(False, "нужно минимум 2 карт.", description="Сопоставляй пары")
    assert not card.isEnabled()
    assert card.hint_text() == "нужно минимум 2 карт."


def test_available_card_shows_description(qt_host) -> None:
    card = ModeCard("Тест", icon_name="checklist", parent=qt_host)
    card.set_available(True, description="Билет с оценкой")
    assert card.isEnabled()
    assert card.hint_text() == "Билет с оценкой"
    assert card.toolTip() == ""


def test_card_icon_dims_when_disabled(qt_host, qt_app) -> None:
    apply_theme(qt_app, Theme.DARK)
    enabled = ModeCard("Тест", icon_name="checklist", parent=qt_host)
    enabled.set_available(True, description="доступен")

    disabled = ModeCard("Тест", icon_name="checklist", parent=qt_host)
    disabled.set_available(False, "недоступен")

    assert enabled.findChild(object, "modeCardIcon").pixmap().toImage() != (
        disabled.findChild(object, "modeCardIcon").pixmap().toImage()
    )


# --- экран ---


def test_every_mode_has_a_card(view) -> None:
    assert all(view.button_for(mode) is not None for mode in StudyMode)


def test_every_mode_has_an_icon() -> None:
    assert set(MODE_ICONS) == set(StudyMode)


def test_cards_describe_their_mode(view) -> None:
    card = view.button_for(StudyMode.FLASHCARDS)
    assert card.title_text() == StudyMode.FLASHCARDS.title
    assert card.hint_text() == StudyMode.FLASHCARDS.description


def test_reason_is_visible_not_only_in_tooltip(services, qt_host) -> None:
    """Причина недоступности должна читаться прямо в карточке."""
    library, decks = services
    deck = library.create("Матан")
    decks.add_card(
        deck.id,
        CardFace.from_text("производная sin x"),
        CardFace((LatexBlock(r"\cos x"),)),
    )
    view = ModeSelectView(decks, parent=qt_host)
    view.load(deck.id)

    card = view.button_for(StudyMode.WRITE)
    assert not card.isEnabled()
    assert "текстовый" in card.hint_text()


def test_reload_restores_description_when_deck_grows(services, qt_host) -> None:
    """Набор дополнили — карточка снова активна и показывает описание."""
    library, decks = services
    deck = library.import_tsv("Франция\tПариж", "Гео")
    view = ModeSelectView(decks, parent=qt_host)
    view.load(deck.id)
    assert not view.button_for(StudyMode.MATCH).isEnabled()

    decks.add_card(deck.id, CardFace.from_text("Италия"), CardFace.from_text("Рим"))
    view.load(deck.id)

    card = view.button_for(StudyMode.MATCH)
    assert card.isEnabled()
    assert card.hint_text() == StudyMode.MATCH.description


def test_refresh_icons_after_theme_change(view, qt_app) -> None:
    apply_theme(qt_app, Theme.DARK)
    view.refresh_icons()
    before = view.button_for(StudyMode.FLASHCARDS).findChild(object, "modeCardIcon")
    dark = before.pixmap().toImage()

    apply_theme(qt_app, Theme.LIGHT)
    view.refresh_icons()
    light = before.pixmap().toImage()

    assert dark != light
