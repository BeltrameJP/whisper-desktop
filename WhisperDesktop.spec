# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Whisper Desktop (macOS .app bundle).

Used only for the macOS release build. Adds the NSMicrophoneUsageDescription
key to the bundle's Info.plist, which macOS requires before an app may access
the microphone. Without it, CoreAudio/TCC silently denies mic access and the
app captures only silence.
"""

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for package in ("faster_whisper", "ctranslate2", "sounddevice", "scipy", "tkinter"):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="WhisperDesktop",
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
    name="WhisperDesktop",
)

app = BUNDLE(
    coll,
    name="WhisperDesktop.app",
    icon=None,
    bundle_identifier="com.beltramejp.whisper-desktop",
    info_plist={
        "CFBundleName": "Whisper Desktop",
        "CFBundleDisplayName": "Whisper Desktop",
        "NSMicrophoneUsageDescription": (
            "Whisper Desktop needs microphone access to transcribe your speech."
        ),
    },
)
