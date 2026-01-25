# -*- mode: python ; coding: utf-8 -*-

import re
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.building.build_main import Analysis, PYZ, EXE
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

# --- Read version from pyproject.toml (PEP 621 static version) ---
pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
m = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"\s*$', pyproject)
version = m.group(1) if m else "0.0.0"

# --- Embed version into the bundled app as a normal Python module ---
# This file will be included because it lives under src/backupctl/
Path("src/backupctl/_version.py").write_text(f'__version__ = "{version}"\n', encoding="utf-8")

# --- (Optional) Also bundle distribution metadata for importlib.metadata.version() ---
datas = []
try:
    datas += copy_metadata("backupctl")  # requires backupctl to be installed in the build env
except Exception:
    pass

a = Analysis(
    ['src/backupctl/__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=collect_submodules("backupctl"),
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
    name='backupctl',
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
    onefile=True
)
