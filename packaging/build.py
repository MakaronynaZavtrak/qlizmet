"""Сборка приложения в исполняемый файл.

Запуск: ``python packaging/build.py``. Результат появится в ``dist/qlizmet``.
Сборка платформозависима: собирать под Windows нужно на Windows, под macOS — на
macOS. Кросс-сборки PyInstaller не умеет.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SPEC = PROJECT / "packaging" / "qlizmet.spec"


def main() -> int:
    if shutil.which("pyinstaller") is None:
        try:
            import PyInstaller  # noqa: F401
        except ImportError:
            print("Не найден PyInstaller. Установите: pip install pyinstaller")
            return 1

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(SPEC),
        "--noconfirm",
        "--distpath",
        str(PROJECT / "dist"),
        "--workpath",
        str(PROJECT / "build"),
    ]
    print("Сборка:", " ".join(command))
    result = subprocess.run(command, cwd=PROJECT)
    if result.returncode == 0:
        print(f"\nГотово: {PROJECT / 'dist' / 'qlizmet'}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
