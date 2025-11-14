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
Name: "startup"; Description: "Run Client on Windows startup"; GroupDescription: "Startup options:"; Check: IsClient; Flags: unchecked exclusive

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
; Startup shortcut for Client (auto-run)
Name: "{commonstartup}\ELM Client"; Filename: "{app}\client.exe"; Check: IsClient

[Run]
; Run Admin immediately after install (only if Admin selected)
Filename: "{app}\admin.exe"; Description: "Launch ELM Admin"; Flags: nowait postinstall; Check: IsAdmin

[UninstallRun]
; Try to stop the Admin process if it's running so files can be removed
Filename: "taskkill.exe"; Parameters: "/IM admin.exe /F"; Flags: runhidden

[UninstallDelete]
; Remove the Admin executable specifically. Do not forcibly delete the whole
; application folder because Client may be installed in the same directory.
Type: files; Name: "{app}\admin.exe"
; Remove the application folder if it became empty after deleting files
Type: dirifempty; Name: "{app}"

[Code]
var
  InstallTypePage: TInputOptionWizardPage;

// Utility: returns the selected role index or -1 when unknown/not yet created.
function RoleSelectedIndex(): Integer;
begin
  if not Assigned(InstallTypePage) then
  begin
    Result := -1;
    exit;
  end;
  Result := InstallTypePage.SelectedValueIndex;
end;

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

procedure CurPageChanged(CurPageID: Integer);
begin
  { Hide the Tasks list when Admin role is selected }
  if CurPageID = wpSelectTasks then
  begin
    // Guard: WizardForm may not be available in very early calls
    if Assigned(WizardForm) then
    begin
      if RoleSelectedIndex() = 0 then
        WizardForm.TasksList.Visible := False
      else
        WizardForm.TasksList.Visible := True;
    end;
  end;
end;

function IsAdmin: Boolean;
begin
  Result := (RoleSelectedIndex() = 0);
end;

function IsClient: Boolean;
begin
  Result := (RoleSelectedIndex() = 1);
end;

// Process-check helper removed. We don't rely on running process detection in
// the installer; instead we check for already-installed component files.

function InitializeSetup(): Boolean;
begin
  // If role selection is not available (e.g. silent/automated run), allow
  // the installer to proceed — selection should be provided via command line
  // switches or default behavior in that case.
  if RoleSelectedIndex() = -1 then
  begin
    Result := True;
    exit;
  end;

  // Only cancel installation when the exact component file for the selected
  // role already exists in expected install locations.
  if IsAdmin then
  begin
    if FileExists(ExpandConstant('{autopf}\ELM\admin.exe')) or FileExists(ExpandConstant('{commonappdata}\ELM\admin.exe')) then
    begin
      MsgBox('ELM Admin is already installed on this computer. The Admin installation will be canceled.', mbInformation, MB_OK);
      Result := False;
      exit;
    end;
  end
  else if IsClient then
  begin
    if FileExists(ExpandConstant('{autopf}\ELM\client.exe')) or FileExists(ExpandConstant('{commonappdata}\ELM\client.exe')) then
    begin
      MsgBox('ELM Client is already installed on this computer. The Client installation will be canceled.', mbInformation, MB_OK);
      Result := False;
      exit;
    end;
  end;

  Result := True;
end;

