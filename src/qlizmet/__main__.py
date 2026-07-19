"""Точка входа приложения: ``python -m qlizmet``.

Импорт Qt намеренно отложен внутрь ``main()``: так ``import qlizmet`` в тестах
и в ядре не тянет за собой PySide6.
"""
from __future__ import annotations

import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from qlizmet.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
