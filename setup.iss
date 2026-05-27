[Setup]
AppName=Hermes Voice Bridge
AppVersion=1.0.0
DefaultDirName={autopf}\HermesVoiceBridge
DefaultGroupName=Hermes Voice Bridge
OutputDir=Output
OutputBaseFilename=HermesVoiceBridge_Installer
SetupIconFile=src\ui\app\public\favicon.ico
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Start automatically with Windows"; GroupDescription: "Autostart"; Flags: unchecked

[Files]
Source: "dist\HermesVoiceBridge\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Hermes Voice Bridge"; Filename: "{app}\HermesVoiceBridge.exe"
Name: "{group}\Uninstall Hermes Voice Bridge"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Hermes Voice Bridge"; Filename: "{app}\HermesVoiceBridge.exe"; Tasks: desktopicon
Name: "{userstartup}\Hermes Voice Bridge"; Filename: "{app}\HermesVoiceBridge.exe"; Tasks: autostart

[Run]
Filename: "{app}\HermesVoiceBridge.exe"; Description: "{cm:LaunchProgram,Hermes Voice Bridge}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
