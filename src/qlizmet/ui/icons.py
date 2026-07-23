"""Набор иконок приложения.

Иконки вшиты в исходники как SVG-строки: так не нужны ни файлы ресурсов, ни
сторонние библиотеки, ни лицензии на чужой набор. Все рисунки — простые
геометрические контуры в сетке 24×24 с обводкой в 2 пункта.

Цвет подставляется при отрисовке из активной темы, поэтому иконки читаются и на
светлой, и на тёмной. Кнопка помнит имя своей иконки, и ``refresh_icons``
перерисовывает их все после смены темы.
"""
from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

from qlizmet.ui.theme import current_palette

#: В этом свойстве кнопка хранит имя своей иконки — чтобы перерисовать при смене темы.
ICON_NAME_PROPERTY = "iconName"
DEFAULT_SIZE = 18

_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="{color}" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
)

#: Тела иконок. Ключ — имя, значение — содержимое svg.
SHAPES: dict[str, str] = {
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "pencil": '<path d="M4 20h4l10-10-4-4L4 16v4z"/><path d="M14 6l4 4"/>',
    "trash": '<path d="M4 7h16"/><path d="M9 7V4h6v3"/>'
             '<path d="M6 7l1 13h10l1-13"/><path d="M10 11v6M14 11v6"/>',
    "arrow-left": '<path d="M19 12H5"/><path d="M11 6l-6 6 6 6"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>',
    "arrow-up": '<path d="M12 19V5"/><path d="M6 11l6-6 6 6"/>',
    "arrow-down": '<path d="M12 5v14"/><path d="M6 13l6 6 6-6"/>',
    "chart": '<path d="M4 20h16"/><path d="M7 20v-7M12 20V6M17 20v-4"/>',
    "cards": '<rect x="3" y="6" width="13" height="14" rx="2"/>'
             '<path d="M8 3h11a2 2 0 0 1 2 2v11"/>',
    "repeat": '<path d="M4 12a8 8 0 0 1 13.7-5.7L20 8"/>'
              '<path d="M20 4v4h-4"/>'
              '<path d="M20 12a8 8 0 0 1-13.7 5.7L4 16"/>'
              '<path d="M4 20v-4h4"/>',
    "checklist": '<path d="M4 7l2 2 3-3"/><path d="M4 17l2 2 3-3"/>'
                 '<path d="M13 8h7M13 18h7"/>',
    "grid": '<rect x="4" y="4" width="7" height="7" rx="1"/>'
            '<rect x="13" y="4" width="7" height="7" rx="1"/>'
            '<rect x="4" y="13" width="7" height="7" rx="1"/>'
            '<rect x="13" y="13" width="7" height="7" rx="1"/>',
    "falling": '<path d="M12 3v13"/><path d="M7 11l5 5 5-5"/><path d="M5 21h14"/>',
    "check": '<path d="M5 13l4 4L19 7"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "download": '<path d="M12 4v11"/><path d="M7 11l5 5 5-5"/>'
                '<path d="M5 20h14"/>',
    "sun": '<circle cx="12" cy="12" r="4"/>'
           '<path d="M12 2v2M12 20v2M2 12h2M20 12h2"/>'
           '<path d="M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19"/>',
    "moon": '<path d="M20 14A8 8 0 0 1 10 4a8 8 0 1 0 10 10z"/>',
}


class UnknownIcon(KeyError):
    """Иконки с таким именем нет."""


@lru_cache(maxsize=256)
def _render(name: str, color: str, size: int) -> QPixmap:
    body = SHAPES.get(name)
    if body is None:
        raise UnknownIcon(name)

    svg = _TEMPLATE.format(color=color, body=body)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    return pixmap


def icon(name: str, *, color: str | None = None, size: int = DEFAULT_SIZE) -> QIcon:
    """Иконка по имени. Цвет по умолчанию — основной цвет текста активной темы."""
    return QIcon(_render(name, color or current_palette().text, size))


def set_icon(widget: QWidget, name: str, *, size: int = DEFAULT_SIZE) -> None:
    """Поставить виджету иконку и запомнить её имя для перерисовки при смене темы."""
    if name not in SHAPES:
        raise UnknownIcon(name)
    widget.setProperty(ICON_NAME_PROPERTY, name)
    widget.setIcon(icon(name, size=size))


def refresh_icons(root: QWidget, *, size: int = DEFAULT_SIZE) -> None:
    """Перерисовать иконки всех потомков ``root`` в цветах текущей темы."""
    for child in root.findChildren(QWidget):
        name = child.property(ICON_NAME_PROPERTY)
        if name and hasattr(child, "setIcon"):
            child.setIcon(icon(name, size=size))
