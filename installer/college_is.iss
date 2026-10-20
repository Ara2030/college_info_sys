; ============================================================================
;  Установщик «Информационная система колледжа» (дипломный проект)
;  Сборка: ISCC.exe installer\college_is.iss   (или build_installer.ps1)
; ============================================================================

#define AppName "Информационная система колледжа"
#define AppVersion "1.0.0"
#define AppPublisher "ИС колледжа (СПО)"
#define AppURL "http://127.0.0.1:8000/"
#define AppId "{{7C1F4A62-9B3E-4D8A-9E51-2A6D0F7B1C34}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName=C:\CollegeIS
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=CollegeIS_Setup_{#AppVersion}
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\_install\app.ico
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=no
AllowNoIcons=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"
Name: "startupicon"; Description: "Запускать систему при входе в Windows"; GroupDescription: "Автозапуск:"; Flags: unchecked

[Files]
Source: "payload\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "payload\install_system.ps1"; DestDir: "{app}\_install"; Flags: ignoreversion
Source: "payload\db\*"; DestDir: "{app}\_install\db"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "payload\sql\*"; DestDir: "{app}\_install\sql"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "payload\wheels\*"; DestDir: "{app}\_install\wheels"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "payload\deps\*"; DestDir: "{app}\_install\deps"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\app.ico"; DestDir: "{app}\_install"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\start.bat"; IconFilename: "{app}\_install\app.ico"; WorkingDir: "{app}"; Comment: "Запуск информационной системы колледжа"
Name: "{group}\Папка установки"; Filename: "{app}"
Name: "{group}\Удалить {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\start.bat"; IconFilename: "{app}\_install\app.ico"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{commonstartup}\{#AppName}"; Filename: "{app}\start.bat"; IconFilename: "{app}\_install\app.ico"; WorkingDir: "{app}"; Tasks: startupicon

[Run]
Filename: "{app}\start.bat"; Description: "Запустить систему сейчас"; Flags: postinstall shellexec nowait skipifsilent; Check: SetupWasOk

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\_install"
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\.env"

[Code]
var
  SetupOk: Boolean;

function SetupWasOk: Boolean;
begin
  Result := SetupOk;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Params: String;
  LogPath: String;
  ShowCmd: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    LogPath := ExpandConstant('{app}\logs\install.log');
    Params := '-NoProfile -ExecutionPolicy Bypass -File "' +
              ExpandConstant('{app}\_install\install_system.ps1') + '" -InstallDir "' +
              ExpandConstant('{app}') + '"' +
              ' -DbName "' + ExpandConstant('{param:DBNAME|college_sys}') + '"' +
              ' -AppRole "' + ExpandConstant('{param:APPROLE|college_app}') + '"';

    if WizardSilent then
    begin
      Params := Params + ' -KeepInstallers';
      ShowCmd := SW_HIDE;
    end
    else
    begin
      WizardForm.StatusLabel.Caption := 'Настройка Python, PostgreSQL и базы данных...';
      ShowCmd := SW_SHOW;
    end;

    if Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Params, '',
            ShowCmd, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) then
    begin
      SetupOk := True;
    end
    else
    begin
      SetupOk := False;
      MsgBox('Не удалось завершить настройку зависимостей (код ' + IntToStr(ResultCode) + ').' + #13#10#13#10 +
             'Установленные файлы сохранены — журнал: ' + LogPath + #13#10 +
             'Исправьте причину и запустите установщик повторно (он продолжит с места ошибки).',
             mbError, MB_OK);
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if UninstallSilent then Exit;
    if MsgBox('Удалить также базу данных PostgreSQL (все данные системы)?',
              mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    begin
      MsgBox('Для удаления базы выполните в pgAdmin или psql:' + #13#10#13#10 +
             '  DROP DATABASE college_sys;' + #13#10 + '  DROP ROLE college_app;' + #13#10#13#10 +
             'Автоматическое удаление отключено, чтобы не потерять данные случайно.',
             mbInformation, MB_OK);
    end;
  end;
end;
