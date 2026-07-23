"""Виджет показа одной стороны карточки.

``FaceView`` рисует произвольную ``CardFace``: текст, картинки и формулы в том
порядке, в каком они лежат в грани. Это базовый кирпич интерфейса — на нём
строятся и сама карточка, и варианты ответов в Learn/Test, и плитки Match.

Виджет устойчив к плохим данным: битая формула и отсутствующий файл картинки
показываются как заметная подпись, но не роняют приложение.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from qlizmet.core.models import CardFace, ImageBlock, LatexBlock, TextBlock
from qlizmet.ui.latex import LatexRenderError, render_latex_png
from qlizmet.ui.theme import current_palette

DEFAULT_MAX_IMAGE_WIDTH = 420


class FaceView(QWidget):
    """Показывает блоки одной стороны карточки."""

    def __init__(
        self,
        face: CardFace | None = None,
        *,
        media_root: Path | str | None = None,
        max_image_width: int = DEFAULT_MAX_IMAGE_WIDTH,
        font_size: int = 14,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._media_root = Path(media_root) if media_root is not None else None
        self._max_image_width = max_image_width
        self._font_size = font_size

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # layout намеренно не сохраняется в атрибут: ссылка на него из виджета
        # вместе с обратной ссылкой родителя образует цикл, на котором сборщик
        # мусора Python и PySide6 могут освободить объект дважды
        self.setLayout(layout)

        self._face = CardFace()
        self.set_face(face or CardFace())

    @property
    def face(self) -> CardFace:
        return self._face

    def block_widgets(self) -> tuple[QWidget, ...]:
        """Виджеты блоков в порядке показа (удобно для тестов)."""
        layout = self.layout()
        return tuple(layout.itemAt(i).widget() for i in range(layout.count()))

    def set_face(self, face: CardFace) -> None:
        """Заменить содержимое на новую грань."""
        self._face = face
        self._clear()
        layout = self.layout()
        for block in face.blocks:
            layout.addWidget(self._widget_for(block))

    # --- внутреннее ---

    def _clear(self) -> None:
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _widget_for(self, block) -> QWidget:
        if isinstance(block, TextBlock):
            return self._text_widget(block)
        if isinstance(block, LatexBlock):
            return self._latex_widget(block)
        if isinstance(block, ImageBlock):
            return self._image_widget(block)
        return self._placeholder("неизвестный тип блока", "faceBlockUnknown")

    def _text_widget(self, block: TextBlock) -> QLabel:
        label = QLabel(block.text)
        label.setObjectName("faceBlockText")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        return label

    def _latex_widget(self, block: LatexBlock) -> QLabel:
        try:
            # цвет берём из активной темы: на тёмном фоне чёрная формула не видна
            png = render_latex_png(
                block.latex,
                font_size=self._font_size,
                color=current_palette().text,
            )
        except LatexRenderError:
            # показываем исходник, чтобы автор карточки увидел, что чинить
            return self._placeholder(block.latex, "faceBlockLatexError")

        pixmap = QPixmap()
        pixmap.loadFromData(png, "PNG")
        label = QLabel()
        label.setObjectName("faceBlockLatex")
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def _image_widget(self, block: ImageBlock) -> QLabel:
        path = self._resolve(block.path)
        pixmap = QPixmap(str(path)) if path.exists() else QPixmap()
        if pixmap.isNull():
            return self._placeholder(
                block.alt or f"нет картинки: {block.path}", "faceBlockImageMissing"
            )

        if pixmap.width() > self._max_image_width:
            pixmap = pixmap.scaledToWidth(
                self._max_image_width, Qt.TransformationMode.SmoothTransformation
            )
        label = QLabel()
        label.setObjectName("faceBlockImage")
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if block.alt:
            label.setToolTip(block.alt)
            label.setAccessibleName(block.alt)
        return label

    def _placeholder(self, text: str, object_name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def _resolve(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.is_absolute() or self._media_root is None:
            return candidate
        return self._media_root / candidate
