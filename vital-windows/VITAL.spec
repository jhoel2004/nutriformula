# -*- mode: python ; coding: utf-8 -*-
"""
Archivo de configuracion para PyInstaller - VITAL para Windows
Genera VITAL.exe con todos los recursos embebidos.
"""

import sys
import os

block_cipher = None

# Rutas de recursos a incluir en el ejecutable
added_files = [
    ('data', 'data'),
    ('assets', 'assets'),
    ('logo.png', '.'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'pandas',
        'numpy',
        'scipy',
        'scipy.optimize',
        'scipy._lib',
        'matplotlib',
        'matplotlib.backends.backend_qtagg',
        'matplotlib.figure',
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.styles',
        'reportlab',
        'reportlab.lib',
        'reportlab.platypus',
        'reportlab.lib.styles',
        'reportlab.lib.pagesizes',
        'qdarkstyle',
        'darkdetect',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'email',
        'http',
        'xml',
        'pydoc',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VITAL',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VITAL',
)
