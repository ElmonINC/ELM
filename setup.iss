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

procedure CurPageChanged(CurPageID: Integer);
begin
  { Hide the Tasks list when Admin role is selected }
  if CurPageID = wpSelectTasks then
  begin
    if Assigned(InstallTypePage) and (InstallTypePage.SelectedValueIndex = 0) then
      WizardForm.TasksList.Visible := False
    else
      WizardForm.TasksList.Visible := True;
  end;
end;

function IsAdmin: Boolean;
begin
  Result := InstallTypePage.SelectedValueIndex = 0;
end;

function IsClient: Boolean;
begin
  Result := InstallTypePage.SelectedValueIndex = 1;
end;

function IsProcessRunning(ProcName: String): Boolean;
var
  ResultCode: Integer;
  Cmd: String;
begin
  // Use cmd.exe /C with piping to find to get an exit code we can check.
  // Escape the pipe with ^ so cmd.exe receives it correctly.
  Cmd := '/C tasklist /FI "IMAGENAME eq ' + ProcName + '" ^| find /I "' + ProcName + '" >NUL';
  if Exec('cmd.exe', Cmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Result := (ResultCode = 0)
  else
    Result := False;
end;

function InitializeSetup(): Boolean;
begin
  // Only block installation if the component being installed is currently running.
  // This allows installing Admin and Client on the same machine (so long as
  // the specific component is not running during its own install).
  if IsAdmin then
  begin
    if IsProcessRunning('admin.exe') then
    begin
      MsgBox('ELM Admin is currently running. Please close admin.exe before installing the Admin component.', mbError, MB_OK);
      Result := False;
      exit;
    end;
  end
  else if IsClient then
  begin
    if IsProcessRunning('client.exe') then
    begin
      MsgBox('ELM Client is currently running. Please close client.exe before installing the Client component.', mbError, MB_OK);
      Result := False;
      exit;
    end;
  end;

  // If install directory already exists, confirm overwrite
  if DirExists(ExpandConstant('{autopf}\ELM')) or DirExists(ExpandConstant('{commonappdata}\ELM')) then
  begin
    if MsgBox('ELM appears to already be installed on this computer. Do you want to continue and overwrite existing installation?', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
      exit;
    end;
  end;

  Result := True;
end;

