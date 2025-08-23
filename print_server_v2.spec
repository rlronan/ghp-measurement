# -*- mode: python ; coding: utf-8 -*-

import os
import escpos

# Get the path to escpos package
escpos_path = os.path.dirname(escpos.__file__)
capabilities_file = os.path.join(escpos_path, 'capabilities.json')

block_cipher = None

a = Analysis(
    ['print_server_v2.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include escpos capabilities data files - create the expected directory structure
        (capabilities_file, 'escpos/capabilities'),
        # Also include the whole escpos package to be safe
        (escpos_path, 'escpos'),
    ],
    hiddenimports=[
        'escpos.printer.network',
        'escpos.printer',
        'escpos.capabilities',
        'escpos.constants',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='print_server_v2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None, 
    codesign_identity=None,
    entitlements_file=None,
)
