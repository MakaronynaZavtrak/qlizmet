"""Экран правки набора: список карточек и операции над ними.

Как и на экране наборов, модальные диалоги живут только в обработчиках кнопок,
а работу делают обычные методы — это позволяет тестировать экран headless.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qlizmet.app.deck_service import DeckService
from qlizmet.core.markup import face_from_markup, face_preview
from qlizmet.core.models import CardFace
from qlizmet.ui.views.card_editor_dialog import CardEditorDialog

CARD_ID_ROLE = Qt.ItemDataRole.UserRole


class DeckEditorView(QWidget):
    """Список карточек набора с добавлением, правкой и перестановкой."""

    back_requested = Signal()

    def __init__(
        self,
        decks: DeckService,
        *,
        media_root: Path | str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._decks = decks
        self._media_root = media_root
        self._deck_id: str | None = None

        back = QPushButton("← К наборам")
        back.setObjectName("backButton")
        back.clicked.connect(self.back_requested.emit)

        self._title = QLabel()
        self._title.setObjectName("deckTitle")
        self._title.setStyleSheet("font-size: 20px; font-weight: 600;")

        self._empty_hint = QLabel("В наборе пока нет карточек — добавьте первую.")
        self._empty_hint.setObjectName("emptyHint")
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hint.setStyleSheet("color: #666;")

        self._list = QListWidget()
        self._list.setObjectName("cardList")
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.itemDoubleClicked.connect(lambda _: self._edit_selected_via_dialog())

        add_button = QPushButton("Добавить")
        add_button.setObjectName("addCardButton")
        add_button.clicked.connect(self._add_via_dialog)

        edit_button = QPushButton("Изменить")
        edit_button.setObjectName("editCardButton")
        edit_button.clicked.connect(self._edit_selected_via_dialog)

        delete_button = QPushButton("Удалить")
        delete_button.setObjectName("deleteCardButton")
        delete_button.clicked.connect(self._delete_selected_via_dialog)

        up_button = QPushButton("↑")
        up_button.setObjectName("moveUpButton")
        up_button.clicked.connect(lambda: self.move_selected(-1))

        down_button = QPushButton("↓")
        down_button.setObjectName("moveDownButton")
        down_button.clicked.connect(lambda: self.move_selected(+1))

        buttons = QHBoxLayout()
        buttons.addWidget(add_button)
        buttons.addWidget(edit_button)
        buttons.addWidget(delete_button)
        buttons.addStretch(1)
        buttons.addWidget(up_button)
        buttons.addWidget(down_button)

        header = QHBoxLayout()
        header.addWidget(back)
        header.addWidget(self._title, stretch=1)

        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addWidget(self._empty_hint)
        layout.addWidget(self._list, stretch=1)
        layout.addLayout(buttons)
        self.setLayout(layout)

    # --- данные ---

    @property
    def deck_id(self) -> str | None:
        return self._deck_id

    def load(self, deck_id: str) -> None:
        self._deck_id = deck_id
        self.refresh()

    def refresh(self) -> None:
        previous = self.selected_card_id()
        self._list.clear()
        if self._deck_id is None:
            return

        deck = self._decks.get(self._deck_id)
        self._title.setText(deck.title)
        for card in deck.cards:
            item = QListWidgetItem(
                f"{face_preview(card.front)}  →  {face_preview(card.back)}"
            )
            item.setData(CARD_ID_ROLE, card.id)
            self._list.addItem(item)

        has_cards = len(deck) > 0
        self._empty_hint.setVisible(not has_cards)
        self._list.setVisible(has_cards)
        if previous:
            self.select_card(previous)

    def card_ids(self) -> list[str]:
        return [
            self._list.item(i).data(CARD_ID_ROLE) for i in range(self._list.count())
        ]

    def selected_card_id(self) -> str | None:
        item = self._list.currentItem()
        return item.data(CARD_ID_ROLE) if item is not None else None

    def select_card(self, card_id: str) -> bool:
        for i in range(self._list.count()):
            if self._list.item(i).data(CARD_ID_ROLE) == card_id:
                self._list.setCurrentRow(i)
                return True
        return False

    # --- действия без диалогов ---

    def add_card(
        self, front: CardFace, back: CardFace, tags: tuple[str, ...] = ()
    ) -> str:
        card = self._decks.add_card(self._require_deck(), front, back, tags)
        self.refresh()
        self.select_card(card.id)
        return card.id

    def add_card_from_markup(
        self, front: str, back: str, tags: tuple[str, ...] = ()
    ) -> str:
        return self.add_card(face_from_markup(front), face_from_markup(back), tags)

    def update_card(
        self,
        card_id: str,
        front: CardFace,
        back: CardFace,
        tags: tuple[str, ...] = (),
    ) -> None:
        self._decks.update_card(self._require_deck(), card_id, front, back, tags)
        self.refresh()
        self.select_card(card_id)

    def delete_card(self, card_id: str) -> bool:
        deleted = self._decks.delete_card(self._require_deck(), card_id)
        self.refresh()
        return deleted

    def move_selected(self, offset: int) -> bool:
        card_id = self.selected_card_id()
        if not card_id:
            return False
        moved = self._decks.move_card(self._require_deck(), card_id, offset)
        if moved:
            self.refresh()
            self.select_card(card_id)
        return moved

    # --- обработчики кнопок (модальные окна только здесь) ---

    def _add_via_dialog(self) -> None:
        if self._deck_id is None:
            return
        dialog = CardEditorDialog(media_root=self._media_root, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and not dialog.is_empty():
            self.add_card(dialog.front_face(), dialog.back_face(), dialog.tags())

    def _edit_selected_via_dialog(self) -> None:
        card_id = self.selected_card_id()
        if self._deck_id is None or not card_id:
            return
        card = self._decks.get(self._deck_id).get_card(card_id)
        if card is None:
            return
        dialog = CardEditorDialog(card, media_root=self._media_root, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and not dialog.is_empty():
            self.update_card(
                card_id, dialog.front_face(), dialog.back_face(), dialog.tags()
            )

    def _delete_selected_via_dialog(self) -> None:
        card_id = self.selected_card_id()
        if not card_id:
            return
        answer = QMessageBox.question(
            self, "Удалить карточку", "Удалить карточку вместе с её прогрессом?"
        )
        if answer is QMessageBox.StandardButton.Yes:
            self.delete_card(card_id)

    def _require_deck(self) -> str:
        if self._deck_id is None:
            raise RuntimeError("набор не загружен")
        return self._deck_id