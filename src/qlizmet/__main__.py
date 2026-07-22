"""Точка входа приложения: ``python -m qlizmet``.

Здесь и только здесь собираются зависимости: открывается база, создаются
репозитории и сервисы, и всё это отдаётся окну. Импорт Qt намеренно отложен
внутрь ``main()``, чтобы ``import qlizmet`` в тестах не тянул PySide6.
"""
from __future__ import annotations

import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from qlizmet.app.library_service import LibraryService
    from qlizmet.app.paths import database_path
    from qlizmet.storage.sqlite.database import connect
    from qlizmet.storage.sqlite.repositories import SqliteDeckRepository
    from qlizmet.ui.main_window import MainWindow

    connection = connect(database_path())
    library = LibraryService(SqliteDeckRepository(connection))

    app = QApplication(sys.argv)
    window = MainWindow(library)
    window.show()
    try:
        return app.exec()
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())