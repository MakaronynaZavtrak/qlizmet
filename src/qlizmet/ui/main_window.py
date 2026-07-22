"""Главное окно приложения: оболочка с переключением экранов."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QWidget

from qlizmet.app.deck_service import DeckService
from qlizmet.app.library_service import LibraryService
from qlizmet.ui.views.deck_editor_view import DeckEditorView
from qlizmet.ui.views.deck_list_view import DeckListView

PAGE_DECK_LIST = "deckListPage"
PAGE_DECK = "deckPage"


class MainWindow(QMainWindow):
    """Оболочка: держит экраны в стопке и переключает их."""

    def __init__(
        self,
        library: LibraryService,
        decks: DeckService,
        *,
        media_root: Path | str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("qlizmet")
        self.resize(900, 600)

        self._library = library

        self._stack = QStackedWidget()

        self._deck_list = DeckListView(library)
        self._deck_list.setObjectName(PAGE_DECK_LIST)
        self._deck_list.deck_opened.connect(self.open_deck)
        self._stack.addWidget(self._deck_list)

        self._deck_editor = DeckEditorView(decks, media_root=media_root)
        self._deck_editor.setObjectName(PAGE_DECK)
        self._deck_editor.back_requested.connect(self.show_deck_list)
        self._stack.addWidget(self._deck_editor)

        self.setCentralWidget(self._stack)
        self.show_deck_list()

    @property
    def deck_list(self) -> DeckListView:
        return self._deck_list

    @property
    def deck_editor(self) -> DeckEditorView:
        return self._deck_editor

    @property
    def current_deck_id(self) -> str | None:
        return self._deck_editor.deck_id if self.current_page() == PAGE_DECK else None

    def current_page(self) -> str:
        """Имя показанного экрана (используется в тестах навигации)."""
        return self._stack.currentWidget().objectName()

    def show_deck_list(self) -> None:
        self._deck_list.refresh()
        self._stack.setCurrentWidget(self._deck_list)

    def open_deck(self, deck_id: str) -> None:
        if self._library.get(deck_id) is None:
            self.show_deck_list()
            return
        self._deck_editor.load(deck_id)
        self._stack.setCurrentWidget(self._deck_editor)