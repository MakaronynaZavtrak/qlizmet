"""Тесты набора иконок и шкалы типографики."""
import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QPushButton  # noqa: E402

from qlizmet.ui.icons import (  # noqa: E402
    ICON_NAME_PROPERTY,
    SHAPES,
    UnknownIcon,
    icon,
    refresh_icons,
    set_icon,
)
from qlizmet.ui.theme import (  # noqa: E402
    DARK,
    FONT_BODY,
    FONT_CAPTION,
    FONT_STACK,
    FONT_TITLE,
    LIGHT,
    Theme,
    apply_theme,
    build_stylesheet,
)


# --- иконки ---


def test_every_icon_renders(qt_app) -> None:
    """Все вшитые иконки должны рисоваться, а не давать пустую картинку."""
    empty = [name for name in SHAPES if icon(name).isNull()]
    assert empty == []


def test_icon_set_is_not_trivial() -> None:
    assert len(SHAPES) >= 12


def test_unknown_icon_raises(qt_app) -> None:
    with pytest.raises(UnknownIcon):
        icon("такой-иконки-нет")


def test_icon_color_follows_theme(qt_app) -> None:
    dark = icon("plus", color=DARK.text).pixmap(18, 18).toImage()
    light = icon("plus", color=LIGHT.text).pixmap(18, 18).toImage()
    assert dark != light


def test_set_icon_remembers_name(qt_host) -> None:
    button = QPushButton(parent=qt_host)
    set_icon(button, "trash")
    assert button.property(ICON_NAME_PROPERTY) == "trash"
    assert not button.icon().isNull()


def test_set_unknown_icon_raises(qt_host) -> None:
    button = QPushButton(parent=qt_host)
    with pytest.raises(UnknownIcon):
        set_icon(button, "нет-такой")


def test_refresh_repaints_icons_after_theme_change(qt_app, qt_host) -> None:
    """После смены темы иконка не должна остаться в старом цвете."""
    from PySide6.QtWidgets import QWidget

    host = QWidget(parent=qt_host)
    button = QPushButton(parent=host)

    apply_theme(qt_app, Theme.DARK)
    set_icon(button, "plus")
    before = button.icon().pixmap(18, 18).toImage()

    apply_theme(qt_app, Theme.LIGHT)
    refresh_icons(host)
    after = button.icon().pixmap(18, 18).toImage()

    assert before != after


def test_refresh_ignores_widgets_without_icons(qt_host) -> None:
    from PySide6.QtWidgets import QLabel, QWidget

    host = QWidget(parent=qt_host)
    QLabel("без иконки", parent=host)
    refresh_icons(host)  # не должно падать


# --- типографика ---


def test_font_stack_is_used() -> None:
    assert FONT_STACK in build_stylesheet(Theme.DARK)


def test_scale_is_ordered() -> None:
    assert FONT_CAPTION < FONT_BODY < FONT_TITLE


def test_scale_reaches_stylesheet() -> None:
    qss = build_stylesheet(Theme.LIGHT)
    assert f"font-size: {FONT_BODY}px" in qss
    assert f"font-size: {FONT_CAPTION}px" in qss
    assert f"font-size: {FONT_TITLE}px" in qss
