"""Экран со списком наборов.

Показывает наборы, умеет создавать, удалять и импортировать их через
``LibraryService``. Модальные диалоги живут только в обработчиках кнопок, а вся
работа вынесена в обычные методы — так экран можно тестировать headless, не
упираясь в блокирующее окно.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qlizmet.app.library_service import LibraryService

DECK_ID_ROLE = Qt.ItemDataRole.UserRole


class DeckListView(QWidget):
    """Список наборов пользователя."""

    deck_opened = Signal(str)

    def __init__(self, library: LibraryService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library

        title = QLabel("Мои наборы")
        title.setObjectName("screenTitle")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")

        self._empty_hint = QLabel("Пока нет ни одного набора — создайте первый.")
        self._empty_hint.setObjectName("emptyHint")
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hint.setStyleSheet("color: #666;")

        self._list = QListWidget()
        self._list.setObjectName("deckList")
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.itemDoubleClicked.connect(lambda _: self.open_selected())

        create_button = QPushButton("Создать")
        create_button.setObjectName("createButton")
        create_button.clicked.connect(self._ask_and_create)

        import_button = QPushButton("Импорт TSV")
        import_button.setObjectName("importButton")
        import_button.clicked.connect(self._ask_and_import)

        delete_button = QPushButton("Удалить")
        delete_button.setObjectName("deleteButton")
        delete_button.clicked.connect(self._confirm_and_delete)

        open_button = QPushButton("Открыть")
        open_button.setObjectName("openButton")
        open_button.clicked.connect(self.open_selected)

        buttons = QHBoxLayout()
        buttons.addWidget(create_button)
        buttons.addWidget(import_button)
        buttons.addStretch(1)
        buttons.addWidget(delete_button)
        buttons.addWidget(open_button)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(self._empty_hint)
        layout.addWidget(self._list, stretch=1)
        layout.addLayout(buttons)
        self.setLayout(layout)

        self.refresh()

    # --- данные ---

    def refresh(self) -> None:
        """Перечитать наборы из хранилища."""
        previous = self.selected_deck_id()
        self._list.clear()
        summaries = self._library.summaries()
        for summary in summaries:
            item = QListWidgetItem(f"{summary.title}  ·  {summary.card_count} карт.")
            item.setData(DECK_ID_ROLE, summary.id)
            if summary.description:
                item.setToolTip(summary.description)
            self._list.addItem(item)

        self._empty_hint.setVisible(not summaries)
        self._list.setVisible(bool(summaries))
        if previous:
            self.select_deck(previous)

    def deck_ids(self) -> list[str]:
        """Идентификаторы наборов в порядке показа (удобно для тестов)."""
        return [
            self._list.item(i).data(DECK_ID_ROLE) for i in range(self._list.count())
        ]

    def selected_deck_id(self) -> str | None:
        item = self._list.currentItem()
        return item.data(DECK_ID_ROLE) if item is not None else None

    def select_deck(self, deck_id: str) -> bool:
        for i in range(self._list.count()):
            if self._list.item(i).data(DECK_ID_ROLE) == deck_id:
                self._list.setCurrentRow(i)
                return True
        return False

    # --- действия (без диалогов, чтобы их можно было тестировать) ---

    def create_deck(self, title: str, description: str = "") -> str:
        deck = self._library.create(title, description)
        self.refresh()
        self.select_deck(deck.id)
        return deck.id

    def import_deck(self, text: str, title: str) -> str:
        deck = self._library.import_tsv(text, title)
        self.refresh()
        self.select_deck(deck.id)
        return deck.id

    def delete_deck(self, deck_id: str) -> bool:
        deleted = self._library.delete(deck_id)
        self.refresh()
        return deleted

    def open_selected(self) -> None:
        deck_id = self.selected_deck_id()
        if deck_id:
            self.deck_opened.emit(deck_id)

    # --- обработчики кнопок (здесь и только здесь модальные окна) ---

    def _ask_and_create(self) -> None:
        title, ok = QInputDialog.getText(self, "Новый набор", "Название:")
        if ok and title.strip():
            self.create_deck(title)

    def _ask_and_import(self) -> None:
        title, ok = QInputDialog.getText(self, "Импорт набора", "Название:")
        if not (ok and title.strip()):
            return
        text, ok = QInputDialog.getMultiLineText(
            self, "Импорт набора", "Строки вида «термин<TAB>определение»:"
        )
        if ok and text.strip():
            self.import_deck(text, title)

    def _confirm_and_delete(self) -> None:
        deck_id = self.selected_deck_id()
        if not deck_id:
            return
        answer = QMessageBox.question(
            self,
            "Удалить набор",
            "Удалить набор вместе с карточками и прогрессом?",
        )
        if answer is QMessageBox.StandardButton.Yes:
            self.delete_deck(deck_id)