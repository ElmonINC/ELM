# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['client.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'numpy',
        'pandas',
        'scipy',
        'matplotlib',
        'PyQt5',
        'PySide6',
        'setuptools',
        'pkg_resources',
        'cryptography',
        'asyncio',
    ],
    noarchive=False,
    optimize=2,   # enable optimization
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='client',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,      # <--- strip symbols to reduce size
    upx=True,        # <--- compress with UPX
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
