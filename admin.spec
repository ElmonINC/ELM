# -*- mode: python ; coding: utf-8 -*-

# --- Configuration ---
# Use the agreed-upon name for seamless integration with the .iss script
app_name = 'ELM_Admin' 

a = Analysis(
    ['admin.py'],
    pathex=[],
    binaries=[],
    datas=[],
    # --- CRITICAL CHANGES HERE ---
    hiddenimports=[
        # Required for cryptography to function correctly in the bundled EXE
        'cryptography.hazmat.bindings._rust',
        # Required for pynput (hotkey functionality) on Windows/Linux
        'pynput.keyboard._win32', 
        'pynput.keyboard._xorg',
        'pynput.mouse._win32',
        'pynput.mouse._xorg',
        # Rich library sometimes benefits from explicit imports too, though often not strictly necessary
    ],
    # --- END CRITICAL CHANGES ---
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ELM-Admin',  # Updated: Changed 'ElM-admin' to 'ELM_Admin'
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Correct: Ensures the console window is visible for rich/prompt
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico'],
)