"""Главное окно приложения: оболочка с переключением экранов."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QWidget

from qlizmet.app import StatsService
from qlizmet.app.deck_service import DeckService
from qlizmet.app.library_service import LibraryService
from qlizmet.app.study_service import StudyService
from qlizmet.core.study import Direction, StudyMode
from qlizmet.ui.views.deck_editor_view import DeckEditorView
from qlizmet.ui.views.deck_list_view import DeckListView
from qlizmet.ui.views.flashcards_view import FlashcardsView
from qlizmet.ui.views.mode_select_view import ModeSelectView
from qlizmet.ui.views.write_view import WriteView
from qlizmet.ui.views.learn_view import LearnView
from qlizmet.ui.views.gravity_view import GravityView
from qlizmet.ui.views.match_view import MatchView
from qlizmet.ui.views.quiz_view import TestView
from qlizmet.ui.views.stats_view import StatsView

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

#: Все режимы реализованы — экраны есть у каждого.
IMPLEMENTED_MODES = set(StudyMode)


class MainWindow(QMainWindow):
    """Оболочка: держит экраны в стопке и переключает их."""

    def __init__(
        self,
        library: LibraryService,
        decks: DeckService,
        study: StudyService | None = None,
        stats: StatsService | None = None,
        *,
        media_root: Path | str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("qlizmet")
        self.resize(900, 600)

        self._library = library
        self._decks = decks
        self._direction = Direction.FRONT_TO_BACK

        self._stack = QStackedWidget()

        self._deck_list = DeckListView(library)
        self._deck_list.setObjectName(PAGE_DECK_LIST)
        self._deck_list.deck_opened.connect(self.open_deck)

        self._deck_editor = DeckEditorView(decks, media_root=media_root)
        self._deck_editor.setObjectName(PAGE_DECK)
        self._deck_editor.back_requested.connect(self.show_deck_list)
        self._deck_editor.study_requested.connect(self.show_modes)

        self._modes = ModeSelectView(decks, IMPLEMENTED_MODES)
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

        self._deck_editor.stats_requested.connect(self.show_stats)

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
                self._learn,
                self._test,
                self._match,
                self._gravity,
                self._stats_view,
        ):
            self._stack.addWidget(view)

        self.setCentralWidget(self._stack)
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
    def stats_view(self) -> StatsView:
        return self._stats_view

    @property
    def current_deck_id(self) -> str | None:
        return self._deck_editor.deck_id if self.current_page() != PAGE_DECK_LIST else None

    def current_page(self) -> str:
        """Имя показанного экрана (используется в тестах навигации)."""
        return self._stack.currentWidget().objectName()

    # --- навигация ---

    def show_deck_list(self) -> None:
        self._deck_list.refresh()
        self._stack.setCurrentWidget(self._deck_list)

    def open_deck(self, deck_id: str) -> None:
        if self._library.get(deck_id) is None:
            self.show_deck_list()
            return
        self._deck_editor.load(deck_id)
        self._stack.setCurrentWidget(self._deck_editor)

    def show_stats(self) -> None:
        deck_id = self._deck_editor.deck_id
        if deck_id is None:
            return
        self._stats_view.load(deck_id)
        self._stack.setCurrentWidget(self._stats_view)

    def show_modes(self) -> None:
        deck_id = self._deck_editor.deck_id
        if deck_id is None:
            self.show_deck_list()
            return
        self._modes.load(deck_id, self._direction)
        self._stack.setCurrentWidget(self._modes)

    def start_mode(self, mode_value: str) -> None:
        deck_id = self._deck_editor.deck_id
        if deck_id is None:
            self.show_deck_list()
            return
        cards = self._decks.get(deck_id).cards
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

    def _back_to_editor(self) -> None:
        deck_id = self._deck_editor.deck_id
        if deck_id is None:
            self.show_deck_list()
            return
        self._deck_editor.refresh()
        self._stack.setCurrentWidget(self._deck_editor)