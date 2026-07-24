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
    from qlizmet.app.scheduler_service import SchedulerService
    from qlizmet.app.stats_service import StatsService
    from qlizmet.app.study_service import StudyService
    from qlizmet.app.paths import database_path, media_dir
    from qlizmet.app.settings import load_settings, save_settings
    from qlizmet.storage.sqlite.database import connect
    from qlizmet.storage.sqlite.repositories import (
        SqliteDeckRepository,
        SqliteProgressRepository,
    )
    from qlizmet.ui.main_window import MainWindow
    from qlizmet.ui import tray as tray_module
    from qlizmet.ui.theme import Theme, apply_theme

    connection = connect(database_path())
    repository = SqliteDeckRepository(connection)
    progress = SqliteProgressRepository(connection)

    settings = load_settings()
    try:
        theme = Theme(settings.theme)
    except ValueError:
        theme = Theme.DARK

    app = QApplication(sys.argv)
    apply_theme(app, theme)

    # значок в трее может быть недоступен (например, в голой системе без панели)
    tray = tray_module.create()
    minimize_to_tray = settings.minimize_to_tray and tray is not None
    if minimize_to_tray:
        # иначе закрытие последнего окна завершило бы приложение,
        # и сворачивание в трей потеряло бы смысл
        app.setQuitOnLastWindowClosed(False)
    window = MainWindow(
        LibraryService(repository),
        DeckService(repository),
        StudyService(progress),
        StatsService(repository, progress),
        SchedulerService(repository, progress),
        media_root=media_dir(),
        theme=theme,
        tray=tray,
        minimize_to_tray=minimize_to_tray,
    )
    window.set_tray_notice_pending(not settings.tray_notice_shown)
    window.tray_notice_shown.connect(
        lambda: save_settings(load_settings().with_tray_notice_shown())
    )

    if tray is not None:
        tray.open_requested.connect(window.restore_from_tray)
        tray.quit_requested.connect(app.quit)
        tray.show()
        window.update_tray_pending()

    window.show()
    try:
        return app.exec()
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
