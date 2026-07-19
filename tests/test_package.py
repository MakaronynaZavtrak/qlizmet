"""Дымовые тесты структуры пакета — проверяют, что все слои импортируются."""
import importlib

import qlizmet


def test_version_is_defined() -> None:
    assert isinstance(qlizmet.__version__, str)
    assert qlizmet.__version__


def test_layers_importable() -> None:
    for module in (
        "qlizmet.core",
        "qlizmet.core.models",
        "qlizmet.core.study",
        "qlizmet.core.srs",
        "qlizmet.core.grading",
        "qlizmet.core.stats",
        "qlizmet.app",
        "qlizmet.storage",
        "qlizmet.storage.repository",
    ):
        assert importlib.import_module(module) is not None


def test_repository_protocol_exists() -> None:
    from qlizmet.storage.repository import DeckRepository

    assert hasattr(DeckRepository, "list_deck_ids")
