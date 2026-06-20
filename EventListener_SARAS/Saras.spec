# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

comtypes_hidden = collect_submodules('comtypes')
comtypes_datas  = collect_data_files('comtypes')
pyqt6_datas     = collect_data_files('PyQt6')
pyqt6_bins      = collect_dynamic_libs('PyQt6')

a = Analysis(
    ['saras_app.py', 'db_handler.py', 'listener1.py'],
    pathex=[],
    binaries=pyqt6_bins,
    datas=[
        ('Dictionary.db', '.'),
    ] + comtypes_datas + pyqt6_datas,
    hiddenimports=comtypes_hidden + [
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.off',
        'fastapi',
        'fastapi.middleware.cors',
        'httpx',
        'pyperclip',
        'pynput.mouse',
        'pynput.keyboard',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
    ],
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
    name='Saras',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['lotus_coin_v2.ico'],
)