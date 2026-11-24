# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import static_ffmpeg

block_cipher = None

# Recopilar directorio de frontend
datas = [
    ('frontend', 'frontend'),
]

# Recopilar binarios de FFmpeg (ffmpeg.exe y ffprobe.exe de static_ffmpeg)
ffmpeg_pkg_dir = os.path.dirname(static_ffmpeg.__file__)
ffmpeg_bin = os.path.join(ffmpeg_pkg_dir, 'bin')
if os.path.exists(ffmpeg_bin):
    datas.append((ffmpeg_bin, 'static_ffmpeg/bin'))

hidden_imports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'starlette',
    'starlette.routing',
    'starlette.middleware',
    'starlette.middleware.cors',
    'starlette.staticfiles',
    'starlette.responses',
    'pydantic',
    'requests',
    'mutagen',
    'mutagen.mp3',
    'mutagen.id3',
    'mutagen.mp4',
    'mutagen.wave',
    'PIL',
    'PIL.Image',
    'yt_dlp',
    'backend.main',
    'backend.services.metadata_service',
    'backend.services.ytdl_service',
    'backend.services.cleanup_service',
]

a = Analysis(
    ['launcher.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc'],
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
    name='MusicaDow',
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
