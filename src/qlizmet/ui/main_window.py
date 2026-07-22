"""Главное окно приложения: оболочка с переключением экранов."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QWidget

from qlizmet.app.deck_service import DeckService
from qlizmet.app.library_service import LibraryService
from qlizmet.app.study_service import StudyService
from qlizmet.core.study import Direction, StudyMode
from qlizmet.ui.views.deck_editor_view import DeckEditorView
from qlizmet.ui.views.deck_list_view import DeckListView
from qlizmet.ui.views.flashcards_view import FlashcardsView
from qlizmet.ui.views.mode_select_view import ModeSelectView
from qlizmet.ui.views.write_view import WriteView

PAGE_DECK_LIST = "deckListPage"
PAGE_DECK = "deckPage"
PAGE_MODES = "modesPage"
PAGE_FLASHCARDS = "flashcardsPage"
PAGE_WRITE = "writePage"

#: Режимы, у которых уже есть экран. Остальные показываются погашенными.
IMPLEMENTED_MODES = {StudyMode.FLASHCARDS, StudyMode.WRITE}


class MainWindow(QMainWindow):
    """Оболочка: держит экраны в стопке и переключает их."""

    def __init__(
        self,
        library: LibraryService,
        decks: DeckService,
        study: StudyService | None = None,
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

        for view in (
            self._deck_list,
            self._deck_editor,
            self._modes,
            self._flashcards,
            self._write,
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

    def _back_to_editor(self) -> None:
        deck_id = self._deck_editor.deck_id
        if deck_id is None:
            self.show_deck_list()
            return
        self._deck_editor.refresh()
        self._stack.setCurrentWidget(self._deck_editor)