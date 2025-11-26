; ============================================================
; INNO SETUP SCRIPT — FULL VERSION
; ============================================================

[Setup]
AppName=ELM_Client
AppVersion=1.0.0
DefaultDirName={localappdata}\ELM_Client
DefaultGroupName=ELM_Client
OutputDir=output
OutputBaseFilename=YourAppInstaller
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName=ELM_Client

[Files]
; ------------------------------------------------------------
; Main application binary
; ------------------------------------------------------------
Source: "ELM-client.exe"; DestDir: "{app}"; Flags: ignoreversion;

; ------------------------------------------------------------
; Create machine-wide folder for secret
; (placeholder is deleted after install)
; ------------------------------------------------------------
Source: "placeholder.txt"; \
DestDir: "{commonappdata}\ELM_Client"; \
Flags: deleteafterinstall;

[Registry]
; ------------------------------------------------------------
; Auto-start for current user
; ------------------------------------------------------------
Root: HKCU; \
Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
ValueType: string; \
ValueName: "ELM_Client"; \
ValueData: """{app}\ELM-client.exe"""; \
Flags: uninsdeletevalue;

[Code]

var
  AdminKeyPage: TInputMemoWizardPage;

; ------------------------------------------------------------
; Wizard page for the admin key
; ------------------------------------------------------------
procedure InitializeWizard();
begin
  AdminKeyPage := CreateInputMemoPage(
      wpSelectDir,
      'Admin Key',
      'Enter the Admin Key provided to you.',
      'Paste your Admin Key below. It will be written to security.secret.',
      True
  );
  AdminKeyPage.Memo.Lines.Add('');
end;

; ------------------------------------------------------------
; Write machine-wide secret during installation
; ------------------------------------------------------------
procedure CurStepChanged(CurStep: TSetupStep);
var
  SecretPath: String;
begin
  if CurStep = ssInstall then
  begin
    SecretPath := ExpandConstant('{commonappdata}\ELM_Client\security.secret');
    SaveStringToFile(SecretPath, AdminKeyPage.Memo.Text, False);
  end;
end;

; ------------------------------------------------------------
; Remove secret on uninstall
; ------------------------------------------------------------
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  SecretPath: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    SecretPath := ExpandConstant('{commonappdata}\ELM_Client\security.secret');
    if FileExists(SecretPath) then
      DeleteFile(SecretPath);
  end;
end;

; ============================================================
; END OF SCRIPT
; ============================================================
