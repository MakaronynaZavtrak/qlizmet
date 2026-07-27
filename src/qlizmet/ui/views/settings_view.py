"""Экран настроек.

Собирает в одном месте всё, что человек может захотеть выключить: сворачивание
в трей, напоминания, тихие часы и автозапуск. Каждая правка сразу сохраняется —
кнопки «Применить» нет намеренно, она только добавляет способ потерять изменения.

Экран честно показывает, чего в системе нет: без трея сворачивание невозможно,
а автозапуск поддерживается не везде — такие переключатели гаснут и объясняют
причину.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QTime, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from qlizmet.app.autostart import Autostart
from qlizmet.app.settings import Settings, load_settings, save_settings
from qlizmet.ui.theme import GAP, PAD
from qlizmet.ui.widgets.screen_header import ScreenHeader


def _minutes_to_qtime(minutes: int) -> QTime:
    """Минуты от полуночи -> QTime (для показа в поле). 24:00 упираем в 23:59."""
    minutes = max(0, min(minutes, 23 * 60 + 59))
    return QTime(minutes // 60, minutes % 60)


def _qtime_to_minutes(time: QTime) -> int:
    """QTime -> минуты от полуночи."""
    return time.hour() * 60 + time.minute()

NO_TRAY_HINT = "В этой системе нет трея"
NO_AUTOSTART_HINT = "Автозапуск для этой системы не поддерживается"
TRAY_HINT = "Пока приложение свёрнуто в трей, оно продолжает напоминать о повторениях"


class SettingsView(QWidget):
    """Настройки приложения."""

    back_requested = Signal()
    settings_changed = Signal(object)

    def __init__(
        self,
        *,
        autostart: Autostart | None = None,
        tray_available: bool = True,
        loader: Callable[[], Settings] = load_settings,
        saver: Callable[[Settings], None] = save_settings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._autostart = autostart
        self._tray_available = tray_available
        self._load = loader
        self._save = saver
        self._loading = False

        header = ScreenHeader("Настройки", back_text="Назад")
        header.back_requested.connect(self.back_requested.emit)

        self._tray_box = QCheckBox("Сворачивать в трей вместо закрытия")
        self._tray_box.setObjectName("trayCheck")
        self._tray_box.toggled.connect(self._on_changed)

        self._reminders_box = QCheckBox("Напоминать, когда пора повторять")
        self._reminders_box.setObjectName("remindersCheck")
        self._reminders_box.toggled.connect(self._on_changed)

        self._quiet_before = QTimeEdit()
        self._quiet_before.setObjectName("quietBefore")
        self._quiet_before.setDisplayFormat("HH:mm")
        self._quiet_before.timeChanged.connect(self._on_changed)

        self._quiet_after = QTimeEdit()
        self._quiet_after.setObjectName("quietAfter")
        self._quiet_after.setDisplayFormat("HH:mm")
        self._quiet_after.timeChanged.connect(self._on_changed)

        quiet_row = QHBoxLayout()
        quiet_row.addWidget(QLabel("Напоминать с"))
        quiet_row.addWidget(self._quiet_before)
        quiet_row.addWidget(QLabel("до"))
        quiet_row.addWidget(self._quiet_after)
        quiet_row.addStretch(1)

        self._autostart_box = QCheckBox("Запускать при входе в систему")
        self._autostart_box.setObjectName("autostartCheck")
        self._autostart_box.toggled.connect(self._on_autostart_toggled)

        self._hint = QLabel()
        self._hint.setObjectName("hintLabel")
        self._hint.setWordWrap(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(PAD, PAD, PAD, PAD)
        layout.setSpacing(GAP)
        layout.addWidget(header)
        layout.addWidget(self._tray_box)
        layout.addWidget(self._reminders_box)
        layout.addLayout(quiet_row)
        layout.addWidget(self._autostart_box)
        layout.addWidget(self._hint)
        layout.addStretch(1)
        self.setLayout(layout)

        self.reload()

    # --- состояние ---

    def reload(self) -> None:
        """Показать текущие настройки, не вызывая их повторного сохранения."""
        settings = self._load()
        self._loading = True
        try:
            self._tray_box.setChecked(settings.minimize_to_tray)
            self._reminders_box.setChecked(settings.reminders_enabled)
            self._quiet_before.setTime(_minutes_to_qtime(settings.quiet_before))
            self._quiet_after.setTime(_minutes_to_qtime(settings.quiet_after))
            self._autostart_box.setChecked(
                self._autostart is not None and self._autostart.is_enabled()
            )
        finally:
            self._loading = False

        self._tray_box.setEnabled(self._tray_available)
        self._autostart_box.setEnabled(self._autostart is not None)
        self._update_hint()

    def current_settings(self) -> Settings:
        """Настройки в том виде, в каком их показывает экран."""
        stored = self._load()
        return Settings(
            theme=stored.theme,
            reminders_enabled=self._reminders_box.isChecked(),
            last_reminder_date=stored.last_reminder_date,
            minimize_to_tray=self._tray_box.isChecked(),
            tray_notice_shown=stored.tray_notice_shown,
            quiet_before=_qtime_to_minutes(self._quiet_before.time()),
            quiet_after=_qtime_to_minutes(self._quiet_after.time()),
        )

    def hint_text(self) -> str:
        return self._hint.text()

    # --- обработчики ---

    def _on_changed(self) -> None:
        if self._loading:
            return
        settings = self.current_settings()
        self._save(settings)
        self.settings_changed.emit(settings)
        self._update_hint()

    def _on_autostart_toggled(self, checked: bool) -> None:
        if self._loading or self._autostart is None:
            return
        if checked:
            self._autostart.enable()
        else:
            self._autostart.disable()
        self._update_hint()

    def _update_hint(self) -> None:
        if not self._tray_available:
            self._hint.setText(NO_TRAY_HINT)
        elif self._autostart is None:
            self._hint.setText(NO_AUTOSTART_HINT)
        else:
            self._hint.setText(TRAY_HINT)
