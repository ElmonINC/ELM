# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['admin.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclude unnecessary big modules
    excludes=[
        'numpy',
        'pandas',
        'scipy',
        'matplotlib',
        'PyQt5',
        'PySide6',
        'setuptools',
        'pkg_resources',
        'tests',
        'tkinter.test',
        'email',
        'http',
        'xml',
    ],
    noarchive=False,
    optimize=2,  # adds bytecode optimization
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='admin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,      # strip symbols from exe
    upx=True,        # compress with UPX
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
