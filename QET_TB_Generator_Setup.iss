; Inno Setup Script for QET Terminal Block Generator

[Setup]
AppId={{E6805791-7667-4299-A8F8-2B7A8B9CAD0E}
AppName=QET Terminal Block Generator
AppVersion=2.0.0
AppPublisher=Raul Roda & Antigravity
DefaultDirName={autopf}\QET_TB_Generator
DefaultGroupName=QET Terminal Block Generator
AllowNoIcons=yes
OutputDir=c:\Users\x.denecheau\Desktop\PYTHON\BORNIER OTHER\Output
OutputBaseFilename=QET_TB_Generator_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "c:\Users\x.denecheau\Desktop\PYTHON\BORNIER OTHER\dist\QET_TerminalBlock_Generator\QET_TB_Generator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "c:\Users\x.denecheau\Desktop\PYTHON\BORNIER OTHER\dist\QET_TerminalBlock_Generator\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\QET Terminal Block Generator"; Filename: "{app}\QET_TB_Generator.exe"
Name: "{autodesktop}\QET Terminal Block Generator"; Filename: "{app}\QET_TB_Generator.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\QET_TB_Generator.exe"; Description: "{cm:LaunchProgram,QET Terminal Block Generator}"; Flags: nowait postinstall skipifsilent
