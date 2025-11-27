; =====================================================================
; INNO SETUP INSTALLER — MATCHED TO client.py
; =====================================================================

[Setup]
AppName=ELM_Client
AppVersion=2.0
DefaultDirName={localappdata}\ELM_Client
DefaultGroupName=ELM Client
OutputDir=output
OutputBaseFilename=ELM_Client_Installer
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName=ELM Client

; =====================================================================
; FILES
; =====================================================================

[Files]
; Main application EXE (the packaged client.py)
Source: "ELM-client.exe"; DestDir: "{app}"; Flags: ignoreversion;

; Create the APPDATA config folder with a placeholder file
Source: "placeholder.txt"; \
    DestDir: "{userappdata}\ELM_Client_Config"; \
    Flags: deleteafterinstall;

; =====================================================================
; AUTOSTART (MATCHES client.py logic)
; =====================================================================

[Registry]
Root: HKCU; \
    Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; \
    ValueName: "ELM_Client"; \
    ValueData: """{app}\ELM-client.exe"""; \
    Flags: uninsdeletevalue;


; =====================================================================
; CODE SECTION — ADMIN KEY PAGE + SECRET FILE WRITING
; =====================================================================

[Code]

var
  KeyPage: TInputMemoWizardPage;

; ---------------------------------------------------------------------
; Create admin key page
; ---------------------------------------------------------------------
procedure InitializeWizard();
begin
  KeyPage := CreateInputMemoPage(
      wpSelectDir,
      'Security Key',
      'Enter the Admin Secret Key',
      'Paste the Security Key provided by the Admin. This will be saved as the security.secret file used by the client.',
      True
  );

  KeyPage.Memo.Lines.Add('');
end;

; ---------------------------------------------------------------------
; Write key to APPDATA\ELM_Client_Config\security.secret
; ---------------------------------------------------------------------
procedure CurStepChanged(CurStep: TSetupStep);
var
  SecretPath: String;
begin
  if CurStep = ssInstall then
  begin
    SecretPath := ExpandConstant('{userappdata}\ELM_Client_Config\security.secret');
    SaveStringToFile(SecretPath, KeyPage.Memo.Text, False);
  end;
end;

; ---------------------------------------------------------------------
; Delete secret file on uninstall
; ---------------------------------------------------------------------
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  SecretPath: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    SecretPath := ExpandConstant('{userappdata}\ELM_Client_Config\security.secret');
    if FileExists(SecretPath) then
      DeleteFile(SecretPath);
  end;
end;

; =====================================================================
; END OF SCRIPT
; =====================================================================
