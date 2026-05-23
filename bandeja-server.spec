# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# Textual incluye ficheros de datos (CSS, temas) que hay que empaquetar
textual_datas, textual_binaries, textual_hidden = collect_all('textual')

a = Analysis(
    ['bandeja-server.py'],
    pathex=[],
    binaries=textual_binaries,
    datas=textual_datas,
    hiddenimports=[
        # uvicorn usa importación dinámica para loops y protocolos
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        # tkinter para el diálogo de selección de carpeta
        'tkinter',
        'tkinter.filedialog',
        # pydantic v2 usa importación dinámica para validadores
        'pydantic.deprecated.class_validators',
        *textual_hidden,
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['pytest', 'unittest', 'test'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='bandeja-server',
    debug=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,   # Textual TUI requiere consola
    icon=None,
)
