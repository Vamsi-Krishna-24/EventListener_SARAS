# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all of comtypes including the pre-generated UIA bindings in comtypes/gen/
comtypes_hidden = collect_submodules('comtypes')
comtypes_datas  = collect_data_files('comtypes')

a = Analysis(
    ['saras_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('Dictionary.db',            '.'),
        ('lotus_running_green.ico',  '.'),
        ('lotus_sleeping_red.ico',   '.'),
        ('lotus_coin_v2.ico',        '.'),
    ] + comtypes_datas,
    hiddenimports=comtypes_hidden,
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