"""Тесты путей к пользовательским данным."""
from qlizmet.app.paths import ENV_HOME, app_data_dir, database_path, media_dir


def test_env_override_is_used(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_HOME, str(tmp_path / "данные"))
    assert app_data_dir() == tmp_path / "данные"


def test_directory_is_created(tmp_path, monkeypatch) -> None:
    target = tmp_path / "новая"
    monkeypatch.setenv(ENV_HOME, str(target))
    assert app_data_dir().is_dir()


def test_database_lives_in_app_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    assert database_path().parent == tmp_path
    assert database_path().name.endswith(".db")


def test_media_dir_is_created(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_HOME, str(tmp_path))
    assert media_dir().is_dir()
    assert media_dir().parent == tmp_path