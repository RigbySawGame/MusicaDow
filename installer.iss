; Inno Setup Script para MusicaDow
; Permite crear un instalador profesional con asistente, iconos en escritorio y desinstalador.
; Si tienes Inno Setup instalado (https://jrsoftware.org/isdl.php), solo haz clic derecho en este archivo y selecciona "Compile".

#define MyAppName "MusicaDow"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MusicaDow"
#define MyAppURL "http://localhost:8000"
#define MyAppExeName "MusicaDow.exe"

[Setup]
AppId={{9F847253-38B4-4D2A-B981-D9F57628C110}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=instalador_salida
OutputBaseFilename=MusicaDow_Instalador_v1.0
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
