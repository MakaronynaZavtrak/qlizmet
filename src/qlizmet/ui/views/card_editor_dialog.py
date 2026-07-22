"""Диалог правки карточки.

Стороны карточки набираются разметкой (см. ``core.markup``), а рядом сразу
показывается предпросмотр через ``FaceView`` — человек видит, во что превратится
его ``$\\frac{1}{2}$``, не закрывая окно.

Диалог не вызывает ``exec()`` сам: тесты создают его, заполняют поля и читают
результат напрямую, не упираясь в модальное окно.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from qlizmet.core.markup import face_from_markup, face_to_markup
from qlizmet.core.models import Card, CardFace
from qlizmet.ui.widgets.face_view import FaceView

MARKUP_HINT = (
    "Разметка: обычный текст, формула — $\\frac{1}{2}$, "
    "картинка — ![подпись](файл.png)"
)


class CardEditorDialog(QDialog):
    """Правка одной карточки: лицо, оборот, теги."""

    def __init__(
        self,
        card: Card | None = None,
        *,
        media_root: Path | str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Карточка")
        self.resize(720, 520)
        self._media_root = media_root

        self._front_edit = QPlainTextEdit()
        self._front_edit.setObjectName("frontEdit")
        self._back_edit = QPlainTextEdit()
        self._back_edit.setObjectName("backEdit")
        self._tags_edit = QLineEdit()
        self._tags_edit.setObjectName("tagsEdit")
        self._tags_edit.setPlaceholderText("теги через запятую")

        self._front_preview = FaceView(media_root=media_root)
        self._front_preview.setObjectName("frontPreview")
        self._back_preview = FaceView(media_root=media_root)
        self._back_preview.setObjectName("backPreview")

        self._front_edit.textChanged.connect(self._refresh_front)
        self._back_edit.textChanged.connect(self._refresh_back)

        hint = QLabel(MARKUP_HINT)
        hint.setObjectName("markupHint")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow("Теги:", self._tags_edit)

        layout = QVBoxLayout()
        layout.addWidget(hint)
        layout.addWidget(self._side_box("Лицевая сторона", self._front_edit, self._front_preview))
        layout.addWidget(self._side_box("Обратная сторона", self._back_edit, self._back_preview))
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

        if card is not None:
            self.set_card(card)

    def set_card(self, card: Card) -> None:
        self._front_edit.setPlainText(face_to_markup(card.front))
        self._back_edit.setPlainText(face_to_markup(card.back))
        self._tags_edit.setText(", ".join(card.tags))

    def set_markup(self, front: str = "", back: str = "", tags: str = "") -> None:
        self._front_edit.setPlainText(front)
        self._back_edit.setPlainText(back)
        self._tags_edit.setText(tags)

    def front_face(self) -> CardFace:
        return face_from_markup(self._front_edit.toPlainText())

    def back_face(self) -> CardFace:
        return face_from_markup(self._back_edit.toPlainText())

    def tags(self) -> tuple[str, ...]:
        raw = self._tags_edit.text()
        return tuple(tag.strip() for tag in raw.split(",") if tag.strip())

    def is_empty(self) -> bool:
        return self.front_face().is_empty and self.back_face().is_empty

    def _side_box(self, title: str, edit: QPlainTextEdit, preview: FaceView) -> QGroupBox:
        box = QGroupBox(title)
        inner = QVBoxLayout()
        inner.addWidget(edit)
        inner.addWidget(preview)
        box.setLayout(inner)
        return box

    def _refresh_front(self) -> None:
        self._front_preview.set_face(self.front_face())

    def _refresh_back(self) -> None:
        self._back_preview.set_face(self.back_face())