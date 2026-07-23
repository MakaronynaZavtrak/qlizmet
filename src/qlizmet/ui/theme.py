"""Тема оформления: палитры, сборка таблицы стилей, переключение.

Экраны не содержат ни одного цвета — они лишь расставляют ``objectName``, а весь
вид задаётся здесь одной таблицей QSS. Благодаря этому тему можно переключить на
лету, а список цветов лежит в одном месте.

Динамические состояния (верный ответ / ошибка, выбранная плитка) выражаются
свойствами Qt, а не подстановкой стилей в коде: ``set_state(widget, "ok")``.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from PySide6.QtWidgets import QApplication, QWidget


class Theme(Enum):
    LIGHT = "light"
    DARK = "dark"

    @property
    def title(self) -> str:
        return "Светлая" if self is Theme.LIGHT else "Тёмная"

    def toggled(self) -> "Theme":
        return Theme.DARK if self is Theme.LIGHT else Theme.LIGHT


@dataclass(frozen=True, slots=True)
class Palette:
    """Набор цветов темы."""

    window: str
    surface: str
    surface_alt: str
    text: str
    text_muted: str
    border: str
    accent: str
    accent_hover: str
    on_accent: str
    danger: str
    success: str
    selection: str


DARK = Palette(
    window="#16181d",
    surface="#1e2127",
    surface_alt="#262a32",
    text="#e6e8ec",
    text_muted="#9aa1ad",
    border="#333842",
    accent="#1d9e75",
    accent_hover="#25b98a",
    on_accent="#ffffff",
    danger="#e2605f",
    success="#5dcaa5",
    selection="#243b36",
)

LIGHT = Palette(
    window="#f4f5f7",
    surface="#ffffff",
    surface_alt="#eef0f3",
    text="#1c1f24",
    text_muted="#61686f",
    border="#d8dbe0",
    accent="#0f6e56",
    accent_hover="#0c5b47",
    on_accent="#ffffff",
    danger="#b3261e",
    success="#0f6e56",
    selection="#dff0e9",
)

PALETTES = {Theme.LIGHT: LIGHT, Theme.DARK: DARK}

#: Единая шкала отступов и скруглений.
RADIUS = 8
PAD = 20
GAP = 12

#: Активная тема. Нужна тем местам, что рисуют не виджетами, а картинкой
#: (рендер формул) — QSS до них не достаёт.
_current = Theme.DARK


def palette_for(theme: Theme) -> Palette:
    return PALETTES[theme]


def current_theme() -> Theme:
    return _current


def current_palette() -> Palette:
    return PALETTES[_current]


def build_stylesheet(theme: Theme) -> str:
    """Собрать QSS для темы."""
    p = palette_for(theme)
    return f"""
QMainWindow, QDialog {{ background: {p.window}; }}
QWidget {{
    color: {p.text};
    font-size: 14px;
}}
QToolTip {{
    background: {p.surface_alt};
    color: {p.text};
    border: 1px solid {p.border};
    padding: 4px 8px;
}}

QPushButton {{
    background: {p.surface};
    color: {p.text};
    border: 1px solid {p.border};
    border-radius: {RADIUS}px;
    padding: 7px 14px;
}}
QPushButton:hover {{ background: {p.surface_alt}; border-color: {p.accent}; }}
QPushButton:pressed {{ background: {p.surface_alt}; }}
QPushButton:disabled {{ color: {p.text_muted}; border-color: {p.border}; }}

QPushButton[role="primary"] {{
    background: {p.accent};
    color: {p.on_accent};
    border-color: {p.accent};
    font-weight: 600;
}}
QPushButton[role="primary"]:hover {{ background: {p.accent_hover}; border-color: {p.accent_hover}; }}
QPushButton[role="primary"]:disabled {{ background: {p.surface_alt}; color: {p.text_muted}; border-color: {p.border}; }}

QPushButton[role="danger"] {{ color: {p.danger}; border-color: {p.danger}; }}
QPushButton[role="danger"]:hover {{ background: {p.surface_alt}; }}

QPushButton[role="quiet"] {{ background: transparent; border-color: transparent; color: {p.text_muted}; }}
QPushButton[role="quiet"]:hover {{ background: {p.surface_alt}; color: {p.text}; }}

QListWidget {{
    background: {p.surface};
    border: 1px solid {p.border};
    border-radius: {RADIUS}px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 10px 12px;
    border-radius: {RADIUS - 2}px;
    color: {p.text};
}}
QListWidget::item:hover {{ background: {p.surface_alt}; }}
QListWidget::item:selected {{ background: {p.selection}; color: {p.text}; }}

QLineEdit, QPlainTextEdit {{
    background: {p.surface};
    color: {p.text};
    border: 1px solid {p.border};
    border-radius: {RADIUS}px;
    padding: 7px 10px;
    selection-background-color: {p.accent};
    selection-color: {p.on_accent};
}}
QLineEdit:focus, QPlainTextEdit:focus {{ border-color: {p.accent}; }}

QGroupBox {{
    border: 1px solid {p.border};
    border-radius: {RADIUS}px;
    margin-top: 14px;
    padding: 12px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {p.text_muted};
}}

QProgressBar {{
    background: {p.surface_alt};
    border: none;
    border-radius: {RADIUS}px;
    height: 18px;
    text-align: center;
    color: {p.text};
}}
QProgressBar::chunk {{ background: {p.accent}; border-radius: {RADIUS}px; }}

#screenTitle, #deckTitle {{ font-size: 20px; font-weight: 600; }}
#emptyHint, #hintLabel, #markupHint, #kindLabel, #sideLabel, #mistakesLabel {{
    color: {p.text_muted};
}}
#summaryLabel, #scoreLabel {{ font-size: 18px; font-weight: 600; }}
#progressLabel, #clockLabel, #statusLabel {{ color: {p.text_muted}; }}

#faceBlockText {{ font-size: 16px; }}
#faceBlockLatexError, #faceBlockImageMissing, #faceBlockUnknown {{
    color: {p.danger};
    font-style: italic;
}}

*[state="ok"] {{ color: {p.success}; }}
*[state="bad"] {{ color: {p.danger}; }}

QPushButton[state="selected"] {{ border: 2px solid {p.accent}; background: {p.selection}; }}
QPushButton[state="wrong"] {{ border: 2px solid {p.danger}; }}
"""


def apply_theme(app: QApplication, theme: Theme) -> None:
    """Применить тему ко всему приложению."""
    global _current
    _current = theme
    app.setStyleSheet(build_stylesheet(theme))


def set_state(widget: QWidget, state: str) -> None:
    """Задать динамическое состояние виджета (``ok``, ``bad``, ``selected``...).

    QSS не перечитывается сам после смены свойства, поэтому виджет нужно
    «переполировать» — иначе новый стиль не применится.
    """
    widget.setProperty("state", state or None)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


def set_role(widget: QWidget, role: str) -> None:
    """Задать роль кнопки (``primary``, ``danger``, ``quiet``)."""
    widget.setProperty("role", role or None)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)

ROLES = {
    "openButton": "primary",
    "deleteButton": "danger",
    "studyButton": "primary",
    "deleteCardButton": "danger",
    "submitButton": "primary",
    "flipButton": "primary",
    "themeButton": "quiet",
}


def apply_roles(root: QWidget) -> None:
    """Расставить роли всем кнопкам внутри ``root`` по их ``objectName``."""
    for name, role in ROLES.items():
        for widget in root.findChildren(QWidget, name):
            set_role(widget, role)