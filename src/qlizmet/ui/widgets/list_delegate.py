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

PADDING_X = 12
PADDING_Y = 9
LINE_GAP = 3


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

        painter.restore()

    def sizeHint(
        self, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QSize:
        base = super().sizeHint(option, index)
        if not index.data(SUBTITLE_ROLE):
            return base
        line = option.fontMetrics.height()
        return QSize(base.width(), line * 2 + LINE_GAP + PADDING_Y * 2)
