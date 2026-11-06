#ifndef AppVersion
  #define AppVersion "0.2.0"
#endif
#define AppName "CNKI 论文助手"

[Setup]
AppId={{E4CC962D-5F7D-45EF-A95B-41CDDBB5CDB0}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=ZHOUoutlook
AppPublisherURL=https://github.com/ZHOUoutlook/cnki_downloader
DefaultDirName={localappdata}\Programs\CNKIPaperAssistant
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist
OutputBaseFilename=CNKI-Paper-Assistant-{#AppVersion}-Setup-x64
SetupIconFile=app.ico
UninstallDisplayIcon={app}\CNKI-Paper-Assistant.exe
LicenseFile=..\..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\CNKI-Paper-Assistant\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\CNKI-Paper-Assistant.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\CNKI-Paper-Assistant.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\CNKI-Paper-Assistant.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
