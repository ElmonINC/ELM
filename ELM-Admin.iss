; --- ELM SECURE ADMIN INSTALLER SCRIPT ---
; This script packages the PyInstaller-generated EXE into a Windows installer.

#define MyAppName "ELM Secure Admin"
#define MyAppVersion "2.0"
#define MyAppPublisher "ELM Security Systems"
#define MyAppExeName "ELM-Admin.exe"

[Setup]
; Unique application identifier (REQUIRED)
AppId={C8B2A910-4F5C-4821-9321-ABCD12345678}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Installs to C:\Program Files\ELM Secure Admin
DefaultDirName={autopf}\{#MyAppName} 
DefaultGroupName={#MyAppName}

; Allows installation only on 64-bit systems, matching the Python environment
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Requires elevated rights to install into Program Files
PrivilegesRequired=admin

; Output settings
OutputDir=Output
OutputBaseFilename=ELM_Admin_Setup_v2.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; CRITICAL: This line assumes you successfully ran PyInstaller and the executable 
; is located at 'your_script_folder\dist\ELM-Admin.exe'
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; NOTE: The admin_config.json is NOT included here, as the fixed Python code 
; will securely generate it in the user's AppData folder on first run.

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Launch the application after installation. Flags: nowait (don't wait for console to close), postinstall.
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// The previous code block is now redundant because the Python script handles 
// permissions by saving the config to AppData, so no custom Inno Setup code is required here.