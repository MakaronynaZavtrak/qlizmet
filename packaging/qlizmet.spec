# -*- mode: python ; coding: utf-8 -*-
"""Сборка qlizmet в самостоятельное приложение.

Приложению повезло с ресурсами: иконки лежат в коде SVG-строками, а оформление
собирается таблицей стилей на лету — поэтому в сборку не нужно тащить ни одного
внешнего файла, кроме иконки самого приложения.

Собирается «папкой», а не одним файлом: одиночный exe при каждом запуске
распаковывает себя во временный каталог, из-за чего приложение стартует заметно
дольше — для программы, которая живёт в трее и запускается вместе с системой,
это плохой размен.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

PROJECT = Path(SPECPATH).parent          # noqa: F821 - SPECPATH задаёт PyInstaller
APP_NAME = "qlizmet"
ICON_DIR = PROJECT / "packaging" / "icons"

#: Windows требует .ico, macOS — .icns, Linux иконку в исполняемый файл не встраивает.
ICON = None
for candidate in (ICON_DIR / "qlizmet.ico", ICON_DIR / "qlizmet.icns"):
    if candidate.exists():
        ICON = str(candidate)
        break

#: Тяжёлые пакеты, которые тянутся за зависимостями, но приложению не нужны.
# ``unittest`` исключать нельзя: matplotlib тянет его через pyparsing,
# и сборка падает при первом же импорте рендера формул.
EXCLUDES = [
    "tkinter",
    "pytest",
    "IPython",
    "notebook",
    "pandas",
    "scipy",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.Qt3DCore",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia",
    "PySide6.QtQuick",
    "PySide6.QtQml",
]

a = Analysis(                            # noqa: F821
    [str(PROJECT / "packaging" / "launcher.py")],
    pathex=[str(PROJECT / "src")],
    binaries=[],
    datas=[],
    hiddenimports=collect_submodules("qlizmet"),
    hookspath=[],
    excludes=EXCLUDES,
    noarchive=False,
)

pyz = PYZ(a.pure)                        # noqa: F821

exe = EXE(                               # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    strip=False,
    upx=False,
    console=False,                       # окно консоли пользователю не нужно
    icon=ICON,
)

coll = COLLECT(                          # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)

app = BUNDLE(                            # noqa: F821
    coll,
    name=f"{APP_NAME}.app",
    icon=ICON,
    bundle_identifier="com.qlizmet",
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "NSHighResolutionCapable": True,
        # приложение живёт в трее, поэтому в доке ему делать нечего
        "LSUIElement": False,
    },
)
