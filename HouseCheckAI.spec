# -*- mode: python ; coding: utf-8 -*-
import sys

datas = [('theme.qss', '.'), ('assets/chevron.svg', 'assets')]
icon = 'assets/icon.icns' if sys.platform == 'darwin' else 'assets/icon.ico'

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['PySide6.QtSvg'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HouseCheckAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, upx_exclude=[], name='HouseCheckAI')
app = BUNDLE(
    coll,
    name='HouseCheckAI.app',
    icon='assets/icon.icns',
    bundle_identifier='kz.housecheck.ai',
    info_plist={'CFBundleDisplayName': 'HouseCheck AI', 'CFBundleShortVersionString': '2.0.0', 'NSHighResolutionCapable': True, 'NSRequiresAquaSystemAppearance': False},
)
