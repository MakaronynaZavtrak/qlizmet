"""Общие фикстуры для тестов хранилища."""
import pytest

from qlizmet.storage.sqlite.database import connect


@pytest.fixture
def conn():
    """Свежая база SQLite в памяти на каждый тест."""
    connection = connect(":memory:")
    yield connection
    connection.close()