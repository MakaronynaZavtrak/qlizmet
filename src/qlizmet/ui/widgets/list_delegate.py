"""Двухстрочный элемент списка.

Рисует заголовок и приглушённый подзаголовок под ним — так строка читается
гораздо лучше, чем «термин → определение» одной строкой. Цвета берутся из
активной темы, поэтому делегат ничего не знает про конкретную палитру.

Подзаголовок хранится в отдельной роли элемента, а не в его тексте: так поиск и
сортировка по-прежнему работают с осмысленным заголовком.

Если строка — это грань из одной формулы, вместо сырого текста рисуется сама
формула картинкой (роли ``TITLE_LATEX_ROLE`` / ``SUBTITLE_LATEX_ROLE``). Так в
списке видно ``½``, а не ``[формула: \\frac{1}{2}]``.
"""
from __future__ import annotations

from PySide6.QtCore import QModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from qlizmet.ui.latex import LatexRenderError, render_latex_png
from qlizmet.ui.theme import current_palette

#: Роль, в которой лежит вторая строка элемента.
SUBTITLE_ROLE = Qt.ItemDataRole.UserRole + 100
#: Роль с долей выполнения (0..1). Если задана — под строкой рисуется полоска.
PROGRESS_ROLE = Qt.ItemDataRole.UserRole + 101
#: Роль со значком справа: короткий текст акцентным цветом (например, «3 к повторению»).
BADGE_ROLE = Qt.ItemDataRole.UserRole + 102
#: Роли с LaTeX строки: если заданы — строка рисуется формулой, а не текстом.
TITLE_LATEX_ROLE = Qt.ItemDataRole.UserRole + 103
SUBTITLE_LATEX_ROLE = Qt.ItemDataRole.UserRole + 104

PADDING_X = 12
PADDING_Y = 9
LINE_GAP = 3
BAR_HEIGHT = 3
BAR_GAP = 7


class TwoLineDelegate(QStyledItemDelegate):
    """Заголовок и подзаголовок в одном элементе списка."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        #: (latex, цвет, высота) -> QPixmap | None. Формула не меняется между
        #: перерисовками, поэтому картинку считаем один раз.
        self._formula_cache: dict[tuple[str, str, int], QPixmap | None] = {}

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        title = index.data(Qt.ItemDataRole.DisplayRole) or ""
        subtitle = index.data(SUBTITLE_ROLE) or ""

        if not subtitle:
            super().paint(painter, option, index)
            return

        # фон, выделение и наведение рисует сам стиль — чтобы тема управляла ими
        widget = option.widget
        style = widget.style() if widget is not None else None
        if style is not None:
            style.drawPrimitive(
                QStyle.PrimitiveElement.PE_PanelItemViewItem, option, painter, widget
            )

        palette = current_palette()
        painter.save()

        rect = option.rect.adjusted(PADDING_X, PADDING_Y, -PADDING_X, -PADDING_Y)

        badge = index.data(BADGE_ROLE)
        if badge:
            rect = self._draw_badge(painter, rect, str(badge), palette, option)

        title_font = QFont(option.font)
        subtitle_font = QFont(option.font)
        subtitle_font.setPointSizeF(max(option.font.pointSizeF() - 1, 7.0))

        painter.setFont(title_font)
        title_height = painter.fontMetrics().height()
        self._draw_line(
            painter,
            QRect(rect.left(), rect.top(), rect.width(), title_height),
            title,
            index.data(TITLE_LATEX_ROLE),
            QColor(palette.text),
        )

        painter.setFont(subtitle_font)
        subtitle_height = painter.fontMetrics().height()
        self._draw_line(
            painter,
            QRect(
                rect.left(),
                rect.top() + title_height + LINE_GAP,
                rect.width(),
                subtitle_height,
            ),
            subtitle,
            index.data(SUBTITLE_LATEX_ROLE),
            QColor(palette.text_muted),
        )

        progress = index.data(PROGRESS_ROLE)
        if progress is not None:
            self._draw_progress(painter, rect, float(progress), palette)

        painter.restore()

    def _draw_line(
        self,
        painter: QPainter,
        rect: QRect,
        text: str,
        latex,
        color: QColor,
    ) -> None:
        """Нарисовать строку: формулу картинкой, если она задана, иначе текст."""
        if latex:
            pixmap = self._formula_pixmap(str(latex), color.name(), rect.height())
            if pixmap is not None:
                if pixmap.width() > rect.width():
                    pixmap = pixmap.scaledToWidth(
                        rect.width(), Qt.TransformationMode.SmoothTransformation
                    )
                top = rect.top() + (rect.height() - pixmap.height()) // 2
                painter.drawPixmap(rect.left(), top, pixmap)
                return
        painter.setPen(color)
        metrics = painter.fontMetrics()
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            metrics.elidedText(text, Qt.TextElideMode.ElideRight, rect.width()),
        )

    def _formula_pixmap(
        self, latex: str, color: str, max_height: int
    ) -> QPixmap | None:
        """Формула картинкой нужной высоты (или ``None``, если не разобралась)."""
        key = (latex, color, max_height)
        if key in self._formula_cache:
            return self._formula_cache[key]

        pixmap: QPixmap | None = None
        try:
            png = render_latex_png(latex, color=color)
        except LatexRenderError:
            png = None
        if png is not None:
            candidate = QPixmap()
            candidate.loadFromData(png, "PNG")
            if not candidate.isNull():
                if candidate.height() > max_height:
                    candidate = candidate.scaledToHeight(
                        max_height, Qt.TransformationMode.SmoothTransformation
                    )
                pixmap = candidate
        self._formula_cache[key] = pixmap
        return pixmap

    def _draw_badge(self, painter, rect, text, palette, option) -> QRect:
        """Значок у правого края. Возвращает место, оставшееся под текст."""
        painter.save()
        painter.setFont(option.font)
        metrics = painter.fontMetrics()
        width = metrics.horizontalAdvance(text)

        painter.setPen(QColor(palette.accent))
        painter.drawText(
            QRect(rect.right() - width, rect.top(), width, metrics.height()),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            text,
        )
        painter.restore()
        return rect.adjusted(0, 0, -(width + PADDING_X), 0)

    def _draw_progress(self, painter, rect, progress, palette) -> None:
        """Тонкая полоска выполнения по нижнему краю строки."""
        bar = QRect(
            rect.left(),
            rect.bottom() - BAR_HEIGHT + 1,
            rect.width(),
            BAR_HEIGHT,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(palette.surface_alt))
        painter.drawRoundedRect(bar, BAR_HEIGHT / 2, BAR_HEIGHT / 2)

        filled = max(0.0, min(1.0, progress))
        if filled <= 0:
            return
        painter.setBrush(QColor(palette.accent))
        painter.drawRoundedRect(
            QRect(bar.left(), bar.top(), int(bar.width() * filled), bar.height()),
            BAR_HEIGHT / 2,
            BAR_HEIGHT / 2,
        )

    def sizeHint(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QSize:
        base = super().sizeHint(option, index)
        if not index.data(SUBTITLE_ROLE):
            return base
        line = option.fontMetrics.height()
        height = line * 2 + LINE_GAP + PADDING_Y * 2
        if index.data(PROGRESS_ROLE) is not None:
            height += BAR_HEIGHT + BAR_GAP
        return QSize(base.width(), height)
