"""Тесты темы оформления и её переключения."""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from qlizmet.app.deck_service import DeckService  # noqa: E402
from qlizmet.app.library_service import LibraryService  # noqa: E402
from qlizmet.app.paths import ENV_HOME  # noqa: E402
from qlizmet.app.settings import load_settings  # noqa: E402
from qlizmet.core.models import CardFace, LatexBlock  # noqa: E402
from qlizmet.storage.sqlite.repositories import SqliteDeckRepository  # noqa: E402
from qlizmet.ui.main_window import MainWindow  # noqa: E402
from qlizmet.ui.theme import (  # noqa: E402
    LIGHT,
    Theme,
    apply_theme,
    build_stylesheet,
    current_palette,
    palette_for,
    set_role,
    set_state,
)
from qlizmet.ui.widgets.face_view import FaceView  # noqa: E402


# --- сама тема ---


def test_toggled_flips_both_ways() -> None:
    assert Theme.DARK.toggled() is Theme.LIGHT
    assert Theme.LIGHT.toggled() is Theme.DARK


def test_palettes_differ() -> None:
    assert palette_for(Theme.DARK).window != palette_for(Theme.LIGHT).window
    assert palette_for(Theme.DARK).text != palette_for(Theme.LIGHT).text


def test_stylesheet_contains_palette_colors() -> None:
    qss = build_stylesheet(Theme.LIGHT)
    assert LIGHT.accent in qss
    assert LIGHT.window in qss


def test_stylesheets_of_two_themes_differ() -> None:
    assert build_stylesheet(Theme.DARK) != build_stylesheet(Theme.LIGHT)


def test_no_hardcoded_colors_left_in_views() -> None:
    """Экраны не должны сами задавать цвета — всё живёт в теме."""
    from pathlib import Path

    views = Path(__file__).resolve().parents[1] / "src" / "qlizmet" / "ui" / "views"
    offenders = [
        path.name
        for path in views.glob("*.py")
        if "setStyleSheet" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


# --- динамические состояния ---


def test_set_state_marks_widget(qt_host) -> None:
    from PySide6.QtWidgets import QLabel

    label = QLabel(parent=qt_host)
    set_state(label, "ok")
    assert label.property("state") == "ok"


def test_set_state_clears(qt_host) -> None:
    from PySide6.QtWidgets import QLabel

    label = QLabel(parent=qt_host)
    set_state(label, "bad")
    set_state(label, "")
    assert label.property("state") is None


def test_set_role_marks_button(qt_host) -> None:
    from PySide6.QtWidgets import QPushButton

    button = QPushButton(parent=qt_host)
    set_role(button, "primary")
    assert button.property("role") == "primary"


# --- формулы следуют теме ---


def test_latex_color_follows_theme(qt_app, qt_host) -> None:
    """На тёмной теме формула не должна рисоваться почти чёрной."""
    apply_theme(qt_app, Theme.DARK)
    dark_view = FaceView(CardFace((LatexBlock(r"\frac{1}{2}"),)), parent=qt_host)
    dark_image = dark_view.block_widgets()[0].pixmap().toImage()

    apply_theme(qt_app, Theme.LIGHT)
    light_view = FaceView(CardFace((LatexBlock(r"\frac{1}{2}"),)), parent=qt_host)
    light_image = light_view.block_widgets()[0].pixmap().toImage()

    assert dark_image != light_image


def test_current_palette_tracks_applied_theme(qt_app) -> None:
    apply_theme(qt_app, Theme.LIGHT)
    assert current_palette().text == LIGHT.text


# --- переключатель в окне ---


@pytest.fixture
def window(conn, qt_host, tmp_path, monkeypatch) -> MainWindow:
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    repo = SqliteDeckRepository(conn)
    return MainWindow(
        LibraryService(repo), DeckService(repo), theme=Theme.DARK, parent=qt_host
    )


def test_window_starts_with_given_theme(window) -> None:
    assert window.theme is Theme.DARK


def test_toggle_switches_theme(window) -> None:
    assert window.toggle_theme() is Theme.LIGHT
    assert window.theme is Theme.LIGHT
    assert window.toggle_theme() is Theme.DARK


def test_toggle_is_persisted(window) -> None:
    window.toggle_theme()
    assert load_settings().theme == "light"


def test_button_label_shows_target_theme(window) -> None:
    assert "Светлая" in window.deck_list.theme_label()
    window.toggle_theme()
    assert "Тёмная" in window.deck_list.theme_label()


def test_toggle_button_click_works(window) -> None:
    window.deck_list.findChild(object, "themeButton").click()
    assert window.theme is Theme.LIGHT
