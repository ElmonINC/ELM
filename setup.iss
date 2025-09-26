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
; Admin can choose extra icons
Name: "desktopicon"; Description: "Create a desktop icon (Admin only)"; GroupDescription: "Additional icons:"; Flags: unchecked; Check: IsAdmin

[Files]
; Admin exe (only if Admin selected)
Source: "dist\admin.exe"; DestDir: "{app}"; DestName: "admin.exe"; Flags: ignoreversion; Check: IsAdmin

; Client exe (only if Client selected)
Source: "dist\client.exe"; DestDir: "{app}"; DestName: "client.exe"; Flags: ignoreversion; Check: IsClient

; Logo (only if Admin, client runs silently)
Source: "logo.ico"; DestDir: "{app}"; Flags: ignoreversion; Check: IsAdmin

[Icons]
; Desktop shortcut for Admin only
Name: "{autodesktop}\ELM Admin"; Filename: "{app}\admin.exe"; Tasks: desktopicon; Check: IsAdmin

; Startup shortcut for Client (always autorun for all users, no option)
Name: "{commonstartup}\ELM Client"; Filename: "{app}\client.exe"; Check: IsClient

[Run]
; Run Admin immediately after install
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
