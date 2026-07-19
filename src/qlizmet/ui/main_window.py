"""Главное окно приложения."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow

from qlizmet import __version__


class MainWindow(QMainWindow):
    """Пустое главное окно — каркас, на который навешиваются экраны режимов."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("qlizmet")
        self.resize(900, 600)

        placeholder = QLabel(f"qlizmet v{__version__}\nскелет проекта")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(placeholder)
