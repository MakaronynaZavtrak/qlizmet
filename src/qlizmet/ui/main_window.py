"""Главное окно приложения: оболочка с переключением экранов."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget

from qlizmet.app.deck_service import DeckService
from qlizmet.app.library_service import LibraryService
from qlizmet.app.scheduler_service import SchedulerService
from qlizmet.app.stats_service import StatsService
from qlizmet.app.study_service import StudyService
from qlizmet.app.settings import Settings, save_settings
from qlizmet.core.study import Direction, SessionScope, StudyMode
from qlizmet.ui.icons import refresh_icons
from qlizmet.ui.theme import Theme, apply_roles, apply_theme
from qlizmet.ui.views.deck_editor_view import DeckEditorView
from qlizmet.ui.views.deck_list_view import DeckListView
from qlizmet.ui.views.flashcards_view import FlashcardsView
from qlizmet.ui.views.gravity_view import GravityView
from qlizmet.ui.views.learn_view import LearnView
from qlizmet.ui.views.match_view import MatchView
from qlizmet.ui.views.mode_select_view import ModeSelectView
from qlizmet.ui.views.quiz_view import TestView
from qlizmet.ui.views.settings_view import SettingsView
from qlizmet.ui.views.stats_view import StatsView
from qlizmet.ui.views.write_view import WriteView

PAGE_DECK_LIST = "deckListPage"
PAGE_DECK = "deckPage"
PAGE_MODES = "modesPage"
PAGE_FLASHCARDS = "flashcardsPage"
PAGE_WRITE = "writePage"
PAGE_LEARN = "learnPage"
PAGE_TEST = "testPage"
PAGE_MATCH = "matchPage"
PAGE_GRAVITY = "gravityPage"
PAGE_STATS = "statsPage"
PAGE_SETTINGS = "settingsPage"

#: Все режимы реализованы — экраны есть у каждого.
IMPLEMENTED_MODES = set(StudyMode)


class MainWindow(QMainWindow):
    """Оболочка: держит экраны в стопке и переключает их."""

    #: Показали разовое пояснение про сворачивание — его стоит запомнить.
    tray_notice_shown = Signal()

    def __init__(
        self,
        library: LibraryService,
        decks: DeckService,
        study: StudyService | None = None,
        stats: StatsService | None = None,
        scheduler: SchedulerService | None = None,
        *,
        tray=None,
        minimize_to_tray: bool = False,
        autostart=None,
        media_root: Path | str | None = None,
        theme: Theme = Theme.DARK,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self.setWindowTitle("qlizmet")
        self.resize(900, 600)

        self._library = library
        self._decks = decks
        self._scheduler = scheduler
        self._tray = tray
        self._minimize_to_tray = minimize_to_tray
        self._tray_notice_pending = True
        self._direction = Direction.FRONT_TO_BACK

        self._stack = QStackedWidget()

        self._deck_list = DeckListView(library, scheduler=scheduler)
        self._deck_list.setObjectName(PAGE_DECK_LIST)
        self._deck_list.deck_opened.connect(self.open_deck)
        self._deck_list.theme_toggle_requested.connect(self.toggle_theme)
        self._deck_list.settings_requested.connect(self.show_settings)
        self._deck_list.set_next_theme(theme.toggled())

        self._deck_editor = DeckEditorView(decks, media_root=media_root)
        self._deck_editor.setObjectName(PAGE_DECK)
        self._deck_editor.back_requested.connect(self.show_deck_list)
        self._deck_editor.study_requested.connect(self.show_modes)
        self._deck_editor.stats_requested.connect(self.show_stats)
        self._deck_editor.review_requested.connect(self.show_review)

        self._modes = ModeSelectView(decks, IMPLEMENTED_MODES, scheduler=scheduler)
        self._modes.setObjectName(PAGE_MODES)
        self._modes.back_requested.connect(self._back_to_editor)
        self._modes.mode_selected.connect(self.start_mode)

        self._flashcards = FlashcardsView(media_root=media_root)
        self._flashcards.setObjectName(PAGE_FLASHCARDS)
        self._flashcards.back_requested.connect(self.show_modes)

        self._write = WriteView(study, media_root=media_root)
        self._write.setObjectName(PAGE_WRITE)
        self._write.back_requested.connect(self.show_modes)

        self._learn = LearnView(study, media_root=media_root)
        self._learn.setObjectName(PAGE_LEARN)
        self._learn.back_requested.connect(self.show_modes)

        self._test = TestView(study, media_root=media_root)
        self._test.setObjectName(PAGE_TEST)
        self._test.back_requested.connect(self.show_modes)

        self._match = MatchView(media_root=media_root)
        self._match.setObjectName(PAGE_MATCH)
        self._match.back_requested.connect(self.show_modes)

        self._gravity = GravityView(media_root=media_root)
        self._gravity.setObjectName(PAGE_GRAVITY)
        self._gravity.back_requested.connect(self.show_modes)

        self._settings_view = SettingsView(
            autostart=autostart, tray_available=tray is not None
        )
        self._settings_view.setObjectName(PAGE_SETTINGS)
        self._settings_view.back_requested.connect(self.show_deck_list)
        self._settings_view.settings_changed.connect(self._apply_settings)

        self._stats_view = StatsView(stats)
        self._stats_view.setObjectName(PAGE_STATS)
        self._stats_view.back_requested.connect(self._back_to_editor)

        for view in (
            self._deck_list,
            self._deck_editor,
            self._modes,
            self._flashcards,
            self._write,
            self._learn,
            self._test,
            self._match,
            self._gravity,
            self._stats_view,
            self._settings_view,
        ):
            self._stack.addWidget(view)

        self.setCentralWidget(self._stack)
        apply_roles(self)
        self.show_deck_list()

    # --- доступ к экранам ---

    @property
    def deck_list(self) -> DeckListView:
        return self._deck_list

    @property
    def deck_editor(self) -> DeckEditorView:
        return self._deck_editor

    @property
    def modes(self) -> ModeSelectView:
        return self._modes

    @property
    def flashcards(self) -> FlashcardsView:
        return self._flashcards

    @property
    def write(self) -> WriteView:
        return self._write

    @property
    def learn(self) -> LearnView:
        return self._learn

    @property
    def test(self) -> TestView:
        return self._test

    @property
    def match(self) -> MatchView:
        return self._match

    @property
    def gravity(self) -> GravityView:
        return self._gravity

    @property
    def settings_view(self) -> SettingsView:
        return self._settings_view

    @property
    def stats_view(self) -> StatsView:
        return self._stats_view

    @property
    def current_deck_id(self) -> str | None:
        return self._deck_editor.deck_id if self.current_page() != PAGE_DECK_LIST else None

    def current_page(self) -> str:
        """Имя показанного экрана (используется в тестах навигации)."""
        return self._stack.currentWidget().objectName()

    @property
    def theme(self) -> Theme:
        return self._theme

    def toggle_theme(self) -> Theme:
        """Переключить тему, применить её и запомнить выбор."""
        self._theme = self._theme.toggled()
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, self._theme)
        self._deck_list.set_next_theme(self._theme.toggled())
        save_settings(Settings(theme=self._theme.value))
        refresh_icons(self)  # иконки нарисованы цветом старой темы — перерисуем
        self._modes.refresh_icons()  # у карточек режимов иконка своя, картинкой
        if self._tray is not None:
            self._tray.refresh_icon()
        self._refresh_current()
        return self._theme

    def _refresh_current(self) -> None:
        """Перерисовать текущий экран: формулы рисуются картинкой и сами не обновятся."""
        current = self._stack.currentWidget()
        refresh = getattr(current, "refresh", None)
        if callable(refresh):
            refresh()

    # --- жизненный цикл окна ---

    @property
    def minimizes_to_tray(self) -> bool:
        """Свернётся ли окно в трей вместо выхода при закрытии."""
        return self._minimize_to_tray and self._tray is not None

    def set_minimize_to_tray(self, enabled: bool) -> None:
        """Включить или выключить сворачивание в трей прямо сейчас.

        Заодно переставляется поведение всего приложения: пока сворачивание
        включено, закрытие последнего окна не должно завершать программу — и
        наоборот, иначе снятая галочка не подействовала бы до перезапуска.
        """
        self._minimize_to_tray = enabled
        app = QApplication.instance()
        if app is not None:
            app.setQuitOnLastWindowClosed(not self.minimizes_to_tray)

    def _apply_settings(self, settings) -> None:
        self.set_minimize_to_tray(settings.minimize_to_tray)

    def set_tray_notice_pending(self, pending: bool) -> None:
        """Нужно ли при первом сворачивании пояснить, что приложение не закрылось."""
        self._tray_notice_pending = pending

    def closeEvent(self, event) -> None:  # noqa: N802 - имя задано Qt
        """Крестик сворачивает в трей, если так настроено, иначе закрывает.

        Разовое пояснение обязательно: молча исчезнувшее окно человек примет за
        зависшую или закрытую программу и пойдёт запускать её заново.
        """
        if not self.minimizes_to_tray:
            super().closeEvent(event)
            return

        event.ignore()
        self.hide()
        if self._tray_notice_pending:
            self._tray_notice_pending = False
            self._tray.notify_hidden()
            self.tray_notice_shown.emit()

    def restore_from_tray(self) -> None:
        """Показать окно обратно по запросу из трея."""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def update_tray_pending(self) -> None:
        """Обновить счётчик в трее по текущему состоянию наборов."""
        if self._tray is None or self._scheduler is None:
            return
        self._tray.set_pending(self._scheduler.total_pending())

    # --- навигация ---

    def show_deck_list(self) -> None:
        self._deck_list.refresh()
        self._stack.setCurrentWidget(self._deck_list)

    def open_deck(self, deck_id: str) -> None:
        if self._library.get(deck_id) is None:
            self.show_deck_list()
            return
        self._deck_editor.load(deck_id)
        self._refresh_pending(deck_id)
        self._stack.setCurrentWidget(self._deck_editor)

    def show_settings(self) -> None:
        self._settings_view.reload()
        self._stack.setCurrentWidget(self._settings_view)

    def show_stats(self) -> None:
        deck_id = self._deck_editor.deck_id
        if deck_id is None:
            return
        self._stats_view.load(deck_id)
        self._stack.setCurrentWidget(self._stats_view)

    def show_modes(self, scope: SessionScope = SessionScope.ALL) -> None:
        deck_id = self._deck_editor.deck_id
        if deck_id is None:
            self.show_deck_list()
            return
        self._modes.load(deck_id, self._direction)
        self._modes.set_scope(scope)
        self._stack.setCurrentWidget(self._modes)

    def show_review(self) -> None:
        """Занятие по расписанию: тот же экран режимов, но сразу «на сегодня».

        Не запускаем режим сами: на сегодня может выпасть одна карточка, и тогда
        часть режимов недоступна — пусть человек выберет из доступных.
        """
        self.show_modes(SessionScope.DUE_TODAY)

    def start_mode(self, mode_value: str) -> None:
        deck_id = self._deck_editor.deck_id
        if deck_id is None:
            self.show_deck_list()
            return
        # очередь берём с экрана режимов: она уже учитывает выбранную область
        cards = self._modes.scoped_cards() or self._decks.get(deck_id).cards
        mode = StudyMode(mode_value)

        if mode is StudyMode.FLASHCARDS:
            self._flashcards.start(cards, direction=self._direction)
            self._stack.setCurrentWidget(self._flashcards)
        elif mode is StudyMode.WRITE:
            self._write.start(cards, direction=self._direction)
            self._stack.setCurrentWidget(self._write)
        elif mode is StudyMode.LEARN:
            self._learn.start(cards, direction=self._direction)
            self._stack.setCurrentWidget(self._learn)
        elif mode is StudyMode.TEST:
            self._test.start(cards, direction=self._direction)
            self._stack.setCurrentWidget(self._test)
        elif mode is StudyMode.MATCH:
            self._match.start(cards)
            self._stack.setCurrentWidget(self._match)
        elif mode is StudyMode.GRAVITY:
            self._gravity.start(cards, direction=self._direction)
            self._stack.setCurrentWidget(self._gravity)

    def _refresh_pending(self, deck_id: str) -> None:
        """Обновить счётчик на кнопке повторения."""
        if self._scheduler is None:
            self._deck_editor.set_pending(0)
            return
        self._deck_editor.set_pending(self._scheduler.deck_plan(deck_id).total)

    def _back_to_editor(self) -> None:
        deck_id = self._deck_editor.deck_id
        if deck_id is None:
            self.show_deck_list()
            return
        self._deck_editor.refresh()
        self._refresh_pending(deck_id)
        self._stack.setCurrentWidget(self._deck_editor)
