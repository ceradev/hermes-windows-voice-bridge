#define MyAppName "Hermes Voice Bridge"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "Nous Research"
#define MyAppExeName "run_voice_desktop.ps1"

[Setup]
AppId={{A6A6E388-5D7C-4AB4-884E-C9C9AF4A8E41}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\HermesVoiceBridge
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\scripts\run_voice_desktop.ps1
Compression=lzma
SolidCompression=yes
WizardStyle=modern
OutputDir=dist
OutputBaseFilename=HermesVoiceBridge-setup
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "src\*"; DestDir: "{app}\src"; Flags: recursesubdirs ignoreversion
Source: "scripts\*"; DestDir: "{app}\scripts"; Flags: recursesubdirs ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\state"
Name: "{app}\state\logs"
Name: "{app}\state\logs\HermesVoiceBridge"

[Icons]
Name: "{group}\Hermes Voice Bridge"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File \"{app}\scripts\run_voice_desktop.ps1\""
Name: "{group}\Hermes Voice Bridge Tray"; Filename: "powershell.exe"; Parameters: "-WindowStyle Hidden -ExecutionPolicy Bypass -File \"{app}\scripts\run_voice_tray.ps1\""
Name: "{group}\Uninstall Hermes Voice Bridge"; Filename: "{uninstallexe}"

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File \"{app}\scripts\install_autostart.ps1\""; Flags: postinstall shellexec skipifsilent unchecked; Description: "Configure tray auto-start"
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File \"{app}\scripts\run_voice_desktop.ps1\""; Flags: postinstall shellexec nowait skipifsilent; Description: "Launch Hermes Voice Bridge"
