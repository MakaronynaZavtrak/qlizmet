"""Тесты согласованности установщика с самим приложением.

Установщик и программа управляют одними и теми же вещами: записью автозапуска в
реестре и версией. Если их развести, ошибка будет из самых неприятных — тихой.
Например, установщик пропишет автозапуск под одним именем, а переключатель в
настройках будет искать другое: галочка покажет «выключено», хотя приложение
исправно стартует при входе в систему.

Настоящую сборку эти тесты не делают — только сверяют тексты.
"""
from pathlib import Path

import pytest

from qlizmet import __version__
from qlizmet.app.autostart import APP_ID, STARTUP_FLAG, RegistryAutostart

PACKAGING = Path(__file__).resolve().parents[1] / "packaging"
INSTALLER = PACKAGING / "windows" / "qlizmet.iss"
VERSION_INCLUDE = PACKAGING / "windows" / "version.iss"
SPEC = PACKAGING / "qlizmet.spec"


@pytest.fixture(scope="module")
def installer_text() -> str:
    if not INSTALLER.exists():
        pytest.skip("скрипт установщика не найден")
    return INSTALLER.read_text(encoding="utf-8")


def test_installer_exists() -> None:
    assert INSTALLER.exists()


def test_registry_key_matches_application(installer_text) -> None:
    """Ветка реестра должна быть той же, что использует приложение."""
    assert RegistryAutostart.KEY.replace("\\", "\\") in installer_text


def test_registry_value_name_matches_app_id(installer_text) -> None:
    """Иначе установщик и настройки вели бы два разных автозапуска."""
    assert f'ValueName: "{APP_ID}"' in installer_text


def test_installer_passes_startup_flag(installer_text) -> None:
    """Без флага приложение при входе в систему открывало бы окно на весь экран."""
    assert STARTUP_FLAG in installer_text


def test_autostart_is_not_forced(installer_text) -> None:
    """Молча прописываться в автозагрузку нельзя — галочка должна быть снята."""
    autostart_task = next(
        line for line in installer_text.splitlines() if 'Name: "autostart"' in line
    )
    assert "unchecked" in autostart_task or "unchecked" in installer_text


def test_desktop_shortcut_is_optional(installer_text) -> None:
    assert 'Tasks: desktopicon' in installer_text


def test_installer_does_not_need_admin(installer_text) -> None:
    """Права администратора приложению не нужны: данные лежат в профиле."""
    assert "PrivilegesRequired=lowest" in installer_text


def _section(text: str, name: str) -> list[str]:
    """Строки указанной секции без комментариев."""
    lines: list[str] = []
    inside = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("["):
            inside = line.lower() == f"[{name.lower()}]"
            continue
        if inside and line and not line.startswith(";"):
            lines.append(line)
    return lines


def test_user_data_survives_uninstall(installer_text) -> None:
    """Удаление программы не должно уносить наборы и прогресс.

    Проверяем именно секцию удаления: в комментариях каталог данных упоминаться
    может и должен, а вот удаляться — нет.
    """
    removed = " ".join(_section(installer_text, "UninstallDelete"))
    assert "{userappdata}" not in removed
    assert "qlizmet.db" not in removed


def test_version_include_matches_package(installer_text) -> None:
    if not VERSION_INCLUDE.exists():
        pytest.skip("version.iss ещё не сгенерирован сборкой")
    assert f'"{__version__}"' in VERSION_INCLUDE.read_text(encoding="utf-8")


def test_installer_uses_generated_version(installer_text) -> None:
    assert "version.iss" in installer_text


def test_spec_and_installer_agree_on_folder_build(installer_text) -> None:
    """Установщик кладёт папку сборки целиком — значит спека не должна делать onefile."""
    spec_text = SPEC.read_text(encoding="utf-8")
    assert "COLLECT" in spec_text
    assert "recursesubdirs" in installer_text
