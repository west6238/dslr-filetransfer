# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=[],
    datas=[('app/assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PySide6.QtWebEngine',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtQml',
        'PySide6.QtQuick',
        'PySide6.Qt3D',
        'PySide6.QtBluetooth',
        'PySide6.QtMultimedia',
        'PySide6.QtSql',
        'PySide6.QtTest',
        'PySide6.QtNetwork',
        'PySide6.QtSensors',
        'PySide6.QtXml',
        'matplotlib', 'numpy', 'pandas', 'PIL'
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Filter out unused PySide6 DLLs to reduce size significantly
unwanted_dlls = [
    'Qt6Qml.dll', 'Qt6QmlMeta.dll', 'Qt6QmlModels.dll', 'Qt6QmlWorkerScript.dll',
    'Qt6Quick.dll', 'Qt6Network.dll', 'Qt6Pdf.dll', 'Qt6VirtualKeyboard.dll',
    'opengl32sw.dll', 'qtvirtualkeyboardplugin.dll', 'qpdf.dll'
]

a.binaries = [b for b in a.binaries if not any(dll in b[0] for dll in unwanted_dlls)]

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DSLR_FileTransfer',
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DSLR_FileTransfer',
)
