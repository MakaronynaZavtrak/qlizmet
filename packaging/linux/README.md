# Сборка под Linux (AppImage)

AppImage — один самодостаточный файл: скачал, `chmod +x`, запустил. Без прав
администратора и без установки в систему (аналог Windows-инсталлятора с
`PrivilegesRequired=lowest`). Данные, как и на других платформах, лежат вне
приложения — в `~/.local/share/qlizmet`, так что переустановка их не трогает.

## Требования

- Собирать **на Linux** (PyInstaller не кросс-компилирует).
- `python`, `curl`, `bash`.
- Зависимости приложения установлены в окружение (PySide6, matplotlib) —
  те же, что и для обычного запуска.

## Как собрать

```sh
python packaging/build.py                 # создаёт dist/qlizmet (PyInstaller)
bash packaging/linux/build_appimage.sh    # оборачивает его в .AppImage
```

Результат: `dist/qlizmet-<версия>-<арх>.AppImage`.
`appimagetool` скачивается автоматически в `build/` при первом запуске.

## Как запустить

```sh
chmod +x qlizmet-*.AppImage
./qlizmet-*.AppImage
```

На системах без `libfuse2` (свежие Ubuntu и пр.) — либо поставить
`sudo apt install libfuse2`, либо запускать так:

```sh
./qlizmet-*.AppImage --appimage-extract-and-run
```

## Интеграция в меню (необязательно)

AppImage самодостаточен и без установки. Чтобы появился ярлык в меню
приложений, используй `AppImageLauncher` (при первом запуске сам предложит
интегрировать) — он возьмёт `qlizmet.desktop` и иконку из образа.

## Файлы

- `build_appimage.sh` — сборочный скрипт (аналог `ISCC qlizmet.iss` на Windows).
- `qlizmet.desktop` — запись для меню и интеграции.
- `AppRun` — точка входа внутри AppImage.
- иконка берётся из `packaging/icons/qlizmet.png`.
