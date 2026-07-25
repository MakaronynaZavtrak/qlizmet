; Установщик qlizmet для Windows (Inno Setup 6).
;
; Собирается так:
;   1) python packaging\build.py          — соберёт dist\qlizmet
;   2) ISCC.exe packaging\windows\qlizmet.iss
; Готовый установщик появится в packaging\windows\output.
;
; Установка идёт в папку пользователя, а не в Program Files: тогда не нужны
; права администратора, а приложению всё равно негде хранить общие данные —
; база лежит в %APPDATA%.

#define AppName "qlizmet"
#define AppPublisher "qlizmet"
#define AppExeName "qlizmet.exe"

; Версию пишет packaging\build.py, чтобы она не разъезжалась с приложением.
#include "version.iss"

[Setup]
AppId={{8F3A6C21-4B7E-4E2C-9E3D-QLIZMET000001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=output
OutputBaseFilename=qlizmet-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=..\icons\qlizmet.ico

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; \
    GroupDescription: "Ярлыки:"
Name: "autostart"; Description: "Запускать при входе в систему"; \
    GroupDescription: "Дополнительно:"; Flags: unchecked

[Files]
; Сборка PyInstaller целиком: exe рядом с папкой _internal.
Source: "..\..\dist\qlizmet\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Та же ветка и то же имя значения, которыми управляет сам qlizmet в настройках,
; поэтому галочка установщика и переключатель в приложении не спорят друг с другом.
; Флаг --startup заставляет приложение стартовать сразу в трей, без окна.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "qlizmet"; \
    ValueData: """{app}\{#AppExeName}"" --startup"; \
    Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Запустить {#AppName}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Данные пользователя (база и картинки в %APPDATA%\qlizmet) намеренно остаются:
; удаление программы не должно уносить с собой набранные карточки и прогресс.
Type: filesandordirs; Name: "{app}\_internal"
