# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['xbox_dash_l3.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/Users/victu/AppData/Local/Programs/Python/Python312/Lib/site-packages/vgamepad/win/vigem', 'vgamepad/win/vigem'), ('app.ico', '.'), ('i18n.py', '.')],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='OniDashL3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OniDashL3',
)
