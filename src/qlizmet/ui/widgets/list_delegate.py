"""Двухстрочный элемент списка.

Рисует заголовок и приглушённый подзаголовок под ним — так строка читается
гораздо лучше, чем «термин → определение» одной строкой. Цвета берутся из
активной темы, поэтому делегат ничего не знает про конкретную палитру.

Подзаголовок хранится в отдельной роли элемента, а не в его тексте: так поиск и
сортировка по-прежнему работают с осмысленным заголовком.
"""
from __future__ import annotations

from PySide6.QtCore import QModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from qlizmet.ui.theme import current_palette

#: Роль, в которой лежит вторая строка элемента.
SUBTITLE_ROLE = Qt.ItemDataRole.UserRole + 100
#: Роль с долей выполнения (0..1). Если задана — под строкой рисуется полоска.
PROGRESS_ROLE = Qt.ItemDataRole.UserRole + 101
#: Роль со значком справа: короткий текст акцентным цветом (например, «3 к повторению»).
BADGE_ROLE = Qt.ItemDataRole.UserRole + 102

PADDING_X = 12
PADDING_Y = 9
LINE_GAP = 3
BAR_HEIGHT = 3
BAR_GAP = 7


class TwoLineDelegate(QStyledItemDelegate):
    """Заголовок и подзаголовок в одном элементе списка."""

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

        metrics_title = painter.fontMetrics()
        painter.setFont(title_font)
        title_height = painter.fontMetrics().height()
        painter.setPen(QColor(palette.text))
        painter.drawText(
            QRect(rect.left(), rect.top(), rect.width(), title_height),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            metrics_title.elidedText(title, Qt.TextElideMode.ElideRight, rect.width()),
        )

        painter.setFont(subtitle_font)
        subtitle_metrics = painter.fontMetrics()
        painter.setPen(QColor(palette.text_muted))
        painter.drawText(
            QRect(
                rect.left(),
                rect.top() + title_height + LINE_GAP,
                rect.width(),
                subtitle_metrics.height(),
            ),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            subtitle_metrics.elidedText(
                subtitle, Qt.TextElideMode.ElideRight, rect.width()
            ),
        )

        progress = index.data(PROGRESS_ROLE)
        if progress is not None:
            self._draw_progress(painter, rect, float(progress), palette)

        painter.restore()

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
