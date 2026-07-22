"""Главное окно приложения: оболочка с переключением экранов."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from qlizmet.app.library_service import LibraryService
from qlizmet.ui.views.deck_list_view import DeckListView

PAGE_DECK_LIST = "deckListPage"
PAGE_DECK = "deckPage"


class MainWindow(QMainWindow):
    """Оболочка: держит экраны в стопке и переключает их."""

    def __init__(
        self, library: LibraryService, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("qlizmet")
        self.resize(900, 600)

        self._library = library
        self._current_deck_id: str | None = None

        self._stack = QStackedWidget()
        self._deck_list = DeckListView(library)
        self._deck_list.setObjectName(PAGE_DECK_LIST)
        self._deck_list.deck_opened.connect(self.open_deck)
        self._stack.addWidget(self._deck_list)

        self._deck_page = self._build_deck_page()
        self._stack.addWidget(self._deck_page)

        self.setCentralWidget(self._stack)
        self.show_deck_list()

    @property
    def deck_list(self) -> DeckListView:
        return self._deck_list

    @property
    def current_deck_id(self) -> str | None:
        return self._current_deck_id

    def current_page(self) -> str:
        """Имя показанного экрана (используется в тестах навигации)."""
        return self._stack.currentWidget().objectName()

    def show_deck_list(self) -> None:
        self._current_deck_id = None
        self._deck_list.refresh()
        self._stack.setCurrentWidget(self._deck_list)

    def open_deck(self, deck_id: str) -> None:
        """Открыть набор. Пока это заглушка — редактор появится следующим шагом."""
        deck = self._library.get(deck_id)
        if deck is None:
            self.show_deck_list()
            return
        self._current_deck_id = deck_id
        self._deck_title.setText(deck.title)
        self._deck_subtitle.setText(f"карточек: {len(deck)}")
        self._stack.setCurrentWidget(self._deck_page)

    def _build_deck_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName(PAGE_DECK)

        self._deck_title = QLabel()
        self._deck_title.setObjectName("deckTitle")
        self._deck_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._deck_title.setStyleSheet("font-size: 22px; font-weight: 600;")

        self._deck_subtitle = QLabel()
        self._deck_subtitle.setObjectName("deckSubtitle")
        self._deck_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("Редактор и режимы появятся на следующих шагах.")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #666;")

        back = QPushButton("← К наборам")
        back.setObjectName("backButton")
        back.clicked.connect(self.show_deck_list)

        layout = QVBoxLayout()
        layout.addWidget(back, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        layout.addWidget(self._deck_title)
        layout.addWidget(self._deck_subtitle)
        layout.addWidget(hint)
        layout.addStretch(1)
        page.setLayout(layout)
        return page