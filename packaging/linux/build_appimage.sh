#!/usr/bin/env bash
# Собирает AppImage из результата PyInstaller (dist/qlizmet).
#
# Собирать под Linux нужно на Linux: PyInstaller не умеет кросс-сборку.
# Порядок (аналог связки build.py + ISCC на Windows):
#   python packaging/build.py                 # создаёт dist/qlizmet
#   bash packaging/linux/build_appimage.sh    # оборачивает его в .AppImage
#
# Готовый файл появится в dist/qlizmet-<версия>-<арх>.AppImage.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$HERE/../.." && pwd)"

DIST="$PROJECT/dist/qlizmet"                    # onedir от PyInstaller (бинарь + _internal)
APPDIR="$PROJECT/build/qlizmet.AppDir"
ICON_SRC="$PROJECT/packaging/icons/qlizmet.png" # уже есть в репозитории

# Версия — из самого пакета, единый источник правды (как в build.py и version.iss).
VERSION="$(cd "$PROJECT" && PYTHONPATH=src python3 -c 'from qlizmet import __version__; print(__version__)')"
ARCH="$(uname -m)"
OUT="$PROJECT/dist/qlizmet-${VERSION}-${ARCH}.AppImage"

[ -d "$DIST" ]       || { echo "Нет $DIST — сначала: python packaging/build.py" >&2; exit 1; }
[ -f "$ICON_SRC" ]   || { echo "Нет иконки $ICON_SRC (нужен PNG)" >&2; exit 1; }
[ -x "$DIST/qlizmet" ] || { echo "В $DIST нет исполняемого qlizmet — проверь сборку PyInstaller" >&2; exit 1; }

echo "Версия: $VERSION, arch: $ARCH"

# 1. Раскладываем AppDir.
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp -a "$DIST"/. "$APPDIR/usr/bin/"

# 2. .desktop + иконка в корень AppDir.
#    Имя иконки (qlizmet.png) обязано совпадать с Icon= в .desktop.
#    .DirIcon — то, что показывают файловые менеджеры для самого .AppImage.
cp "$HERE/qlizmet.desktop" "$APPDIR/qlizmet.desktop"
cp "$ICON_SRC"             "$APPDIR/qlizmet.png"
cp "$ICON_SRC"             "$APPDIR/.DirIcon"

# 3. AppRun.
cp "$HERE/AppRun" "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"

# 4. appimagetool — качаем при отсутствии, под текущую архитектуру.
case "$ARCH" in
  x86_64)  TOOL_ARCH="x86_64" ;;
  aarch64) TOOL_ARCH="aarch64" ;;
  *) echo "Неизвестная архитектура $ARCH — возьми appimagetool вручную" >&2; exit 1 ;;
esac
TOOL="$PROJECT/build/appimagetool-${TOOL_ARCH}.AppImage"
if [ ! -x "$TOOL" ]; then
  echo "Скачиваю appimagetool ($TOOL_ARCH)..."
  curl -fL -o "$TOOL" \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${TOOL_ARCH}.AppImage"
  chmod +x "$TOOL"
fi

# 5. Собираем. APPIMAGE_EXTRACT_AND_RUN=1 позволяет запускать appimagetool
#    там, где нет FUSE (CI, контейнеры, свежие дистрибутивы без libfuse2).
export APPIMAGE_EXTRACT_AND_RUN=1
export ARCH
rm -f "$OUT"
"$TOOL" "$APPDIR" "$OUT"

echo ""
echo "Готово: $OUT"
echo "Запуск: chmod +x '$OUT' && '$OUT'"
