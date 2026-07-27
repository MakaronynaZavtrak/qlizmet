"""Значок приложения в системном трее.

Тонкая обёртка над ``QSystemTrayIcon``: меню, подсказка и сигналы наружу. Всё,
что можно посчитать без Qt — тексты пунктов и подсказки — вынесено в обычные
функции и покрыто тестами; сам трей в headless-среде (например, в CI) просто
недоступен, и приложение обязано работать без него.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QSystemTrayIcon,
    QWidget,
)

from qlizmet.core.plurals import cards as cards_word
from qlizmet.core.srs import PendingCounts
from qlizmet.ui.icons import icon
from qlizmet.ui.theme import current_palette

TRAY_ICON = "bulb"
TRAY_ICON_SIZE = 32

HIDDEN_TITLE = "qlizmet свернулся в трей"
HIDDEN_BODY = "Приложение продолжает работать и напомнит, когда придёт время повторять."


def is_available() -> bool:
    """Есть ли в системе трей. В headless-среде — нет.

    Проверка Qt требует уже созданного ``QApplication``: без него обращение к
    системному трею роняет процесс, а не возвращает False. Поэтому сначала
    убеждаемся, что приложение существует.
    """
    if QApplication.instance() is None:
        return False
    return QSystemTrayIcon.isSystemTrayAvailable()


def pending_label(pending: PendingCounts) -> str:
    """Строка-справка в меню трея."""
    if pending.is_empty:
        return "На сегодня всё повторено"
    total = pending.total
    return f"На сегодня: {total} {cards_word(total)}"


def tray_tooltip(pending: PendingCounts) -> str:
    """Подсказка при наведении на значок."""
    return f"qlizmet — {pending_label(pending)}"


class TrayController(QObject):
    """Значок в трее и его меню."""

    open_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(
            icon(TRAY_ICON, color=current_palette().accent, size=TRAY_ICON_SIZE)
        )
        self._tray.activated.connect(self._on_activated)

        menu = QMenu()
        self._pending_action = menu.addAction(pending_label(PendingCounts()))
        self._pending_action.setEnabled(False)  # это справка, а не кнопка
        menu.addSeparator()
        menu.addAction("Открыть qlizmet").triggered.connect(self.open_requested.emit)
        menu.addSeparator()
        menu.addAction("Выход").triggered.connect(self.quit_requested.emit)
        self._menu = menu
        self._tray.setContextMenu(menu)

        self.set_pending(PendingCounts())

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def set_pending(self, pending: PendingCounts) -> None:
        self._pending_action.setText(pending_label(pending))
        self._tray.setToolTip(tray_tooltip(pending))

    def notify(self, title: str, body: str) -> None:
        """Показать всплывающее уведомление."""
        self._tray.showMessage(title, body, self._tray.icon())

    def notify_hidden(self) -> None:
        """Сообщить, что приложение не закрылось, а свернулось.

        Без этого человек решит, что программа зависла или закрылась насовсем.
        """
        self.notify(HIDDEN_TITLE, HIDDEN_BODY)

    def refresh_icon(self) -> None:
        """Перерисовать значок после смены темы."""
        self._tray.setIcon(
            icon(TRAY_ICON, color=current_palette().accent, size=TRAY_ICON_SIZE)
        )

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.open_requested.emit()


def create(parent: QWidget | None = None) -> TrayController | None:
    """Создать значок в трее или вернуть ``None``, если трея в системе нет."""
    if not is_available():
        return None
    return TrayController(parent)
