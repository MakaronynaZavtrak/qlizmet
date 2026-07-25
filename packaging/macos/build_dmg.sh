#!/usr/bin/env bash
# Собирает .dmg (перетащи-в-Applications) из dist/qlizmet.app.
#
# Собирать под macOS нужно на macOS: PyInstaller не кросс-компилирует.
# Порядок (аналог связки build.py + ISCC на Windows):
#   python packaging/build.py            # создаёт dist/qlizmet.app (spec с BUNDLE)
#   bash packaging/macos/build_dmg.sh    # оборачивает его в .dmg
#
# Готовый файл появится в dist/qlizmet-<версия>.dmg.
# hdiutil входит в macOS, ставить ничего не нужно.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$HERE/../.." && pwd)"
APP="$PROJECT/dist/qlizmet.app"

# Версия — из самого пакета, единый источник правды (как в build.py и spec).
VERSION="$(cd "$PROJECT" && PYTHONPATH=src python3 -c 'from qlizmet import __version__; print(__version__)')"
OUT="$PROJECT/dist/qlizmet-${VERSION}.dmg"

[ -d "$APP" ] || { echo "Нет $APP — сначала: python packaging/build.py (на macOS, spec с BUNDLE)" >&2; exit 1; }

echo "Версия: $VERSION"

# Стейджинг: .app + симлинк на /Applications, чтобы в окне dmg было куда тащить.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

rm -f "$OUT"
hdiutil create \
  -volname "qlizmet ${VERSION}" \
  -srcfolder "$STAGE" \
  -fs HFS+ \
  -format UDZO \
  -ov \
  "$OUT"

echo ""
echo "Готово: $OUT"
