"""Точка входа приложения: ``python -m qlizmet``.

Здесь и только здесь собираются зависимости: открывается база, создаются
репозитории и сервисы, и всё это отдаётся окну. Импорт Qt намеренно отложен
внутрь ``main()``, чтобы ``import qlizmet`` в тестах не тянул PySide6.
"""
from __future__ import annotations

import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from qlizmet.app.deck_service import DeckService
    from qlizmet.app.library_service import LibraryService
    from qlizmet.app.paths import database_path, media_dir
    from qlizmet.app.stats_service import StatsService
    from qlizmet.app.study_service import StudyService
    from qlizmet.storage.sqlite.database import connect
    from qlizmet.storage.sqlite.repositories import (
        SqliteDeckRepository,
        SqliteProgressRepository,
    )
    from qlizmet.ui.main_window import MainWindow

    connection = connect(database_path())
    repository = SqliteDeckRepository(connection)
    progress = SqliteProgressRepository(connection)

    app = QApplication(sys.argv)
    window = MainWindow(
        LibraryService(repository),
        DeckService(repository),
        StudyService(progress),
        StatsService(repository, progress),
        media_root=media_dir(),
    )
    window.show()
    try:
        return app.exec()
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())