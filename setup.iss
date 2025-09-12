; Inno Setup Script for ELM Messaging App
; Save as setup.iss and compile with Inno Setup Compiler

[Setup]
AppName=ELM
AppVersion=1.0
DefaultDirName={autopf}\ELM
DefaultGroupName=ELM
OutputDir=.\Setup
OutputBaseFilename=ELMSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=logo.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "startup"; Description: "Run Client on Windows startup"; GroupDescription: "Startup options:"; Flags: unchecked exclusive

[Files]
; Admin exe
Source: "dist\admin.exe"; DestDir: "{app}"; DestName: "admin.exe"; Flags: ignoreversion
; Client exe
Source: "dist\client.exe"; DestDir: "{app}"; DestName: "client.exe"; Flags: ignoreversion
; Logo
Source: "logo.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Desktop shortcut for Admin
Name: "{autodesktop}\ELM Admin"; Filename: "{app}\admin.exe"; Tasks: desktopicon; Check: IsAdmin
; Desktop shortcut for Client
Name: "{autodesktop}\ELM Client"; Filename: "{app}\client.exe"; Tasks: desktopicon; Check: IsClient
; Startup shortcut for Client (auto-run)
Name: "{commonstartup}\ELM Client"; Filename: "{app}\client.exe"; Check: IsClient

[Run]
; Run Admin immediately after install (only if Admin selected)
Filename: "{app}\admin.exe"; Description: "Launch ELM Admin"; Flags: nowait postinstall; Check: IsAdmin

[Code]
var
  InstallTypePage: TInputOptionWizardPage;

procedure InitializeWizard;
begin
  InstallTypePage := CreateInputOptionPage(wpWelcome,
    'Choose Installation Type',
    'Select whether to install ELM as Admin or Client',
    'Choose the role for this computer:',
    True, False);
  InstallTypePage.Add('Admin (IT Officer)');
  InstallTypePage.Add('Client (End User)');
end;

function IsAdmin: Boolean;
begin
  Result := InstallTypePage.SelectedValueIndex = 0;
end;

function IsClient: Boolean;
begin
  Result := InstallTypePage.SelectedValueIndex = 1;
end;
