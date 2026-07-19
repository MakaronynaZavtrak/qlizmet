"""Тест, что главное окно создаётся. Работает headless через offscreen-платформу."""
import os

import pytest

pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from qlizmet.ui.main_window import MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_title(qt_app) -> None:
    window = MainWindow()
    assert window.windowTitle() == "qlizmet"


def test_main_window_has_central_widget(qt_app) -> None:
    window = MainWindow()
    assert window.centralWidget() is not None
