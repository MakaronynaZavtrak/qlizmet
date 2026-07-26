"""Мелкие помощники для показа граней-формул картинкой.

Грань из одной формулы (без текста и картинок) стоит рисовать самой формулой, а
не сырым ``[формула: ...]``. Здесь — определение такой грани и её рендер в
``QPixmap`` нужной высоты. Используют экраны выбора ответа и делегат списка.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from qlizmet.core.models import CardFace, LatexBlock
from qlizmet.ui.latex import LatexRenderError, render_latex_png


def single_formula(face: CardFace) -> str | None:
    """LaTeX грани, если она состоит ровно из одной формулы, иначе ``None``."""
    blocks = face.blocks
    if len(blocks) == 1 and isinstance(blocks[0], LatexBlock):
        return blocks[0].latex
    return None


def formula_pixmap(latex: str, color: str, max_height: int) -> QPixmap | None:
    """Формула картинкой не выше ``max_height`` (или ``None``, если не разобралась)."""
    try:
        png = render_latex_png(latex, color=color)
    except LatexRenderError:
        return None
    pixmap = QPixmap()
    pixmap.loadFromData(png, "PNG")
    if pixmap.isNull():
        return None
    if pixmap.height() > max_height:
        pixmap = pixmap.scaledToHeight(
            max_height, Qt.TransformationMode.SmoothTransformation
        )
    return pixmap
