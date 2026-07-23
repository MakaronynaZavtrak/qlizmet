"""Общие фикстуры тестов."""
import os

import pytest

from qlizmet.storage.sqlite.database import connect

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def conn():
    """Свежая база SQLite в памяти на каждый тест."""
    connection = connect(":memory:")
    yield connection
    connection.close()


@pytest.fixture(scope="session")
def qt_app():
    """Единственный QApplication на всю сессию тестов."""
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="session")
def qt_host(qt_app):
    """Долгоживущий родитель для виджетов из тестов.

    Виджет без родителя принадлежит Python, и цикличный сборщик мусора может
    освободить его одновременно с C++-объектом — это роняет процесс уже после
    прохождения тестов. Родитель снимает вопрос владения.
    """
    from PySide6.QtWidgets import QWidget

    return QWidget()