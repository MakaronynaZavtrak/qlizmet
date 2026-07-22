"""Тест, что главное окно создаётся. Работает headless через offscreen-платформу."""
import pytest

pytest.importorskip("PySide6")

from qlizmet.ui.main_window import MainWindow  # noqa: E402


def test_main_window_title(qt_host) -> None:
    window = MainWindow(parent=qt_host)
    assert window.windowTitle() == "qlizmet"


def test_main_window_has_central_widget(qt_host) -> None:
    window = MainWindow(parent=qt_host)
    assert window.centralWidget() is not None