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
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

PROJECT = Path(SPECPATH).parent          # noqa: F821 - SPECPATH задаёт PyInstaller
APP_NAME = "qlizmet"
ICON_DIR = PROJECT / "packaging" / "icons"

#: Версия — из самого пакета, единый источник правды (как в build.py).
sys.path.insert(0, str(PROJECT / "src"))
from qlizmet import __version__          # noqa: E402

#: Windows требует .ico, macOS — .icns, Linux иконку в исполняемый файл не встраивает.
#: Формат выбираем по платформе, а не по «какой файл существует»: .ico лежит в
#: репозитории всегда, и при выборе по существованию на macOS в .app цеплялся бы
#: именно он — а мак его как иконку приложения не понимает.
if sys.platform == "darwin":
    _icon_path = ICON_DIR / "qlizmet.icns"
elif sys.platform == "win32":
    _icon_path = ICON_DIR / "qlizmet.ico"
else:
    _icon_path = None
ICON = str(_icon_path) if _icon_path is not None and _icon_path.exists() else None

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
    bundle_identifier="io.github.makaronynazavtrak.qlizmet",
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleShortVersionString": __version__,
        "CFBundleVersion": __version__,
        "NSHighResolutionCapable": True,
        # приложение живёт в трее, поэтому в доке ему делать нечего
        "LSUIElement": False,
    },
)
