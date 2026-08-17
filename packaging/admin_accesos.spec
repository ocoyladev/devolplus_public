# -*- mode: python ; coding: utf-8 -*-
# Spec de PyInstaller para el Admin de accesos de DEVOL+. Construir en Windows:
#   pyinstaller packaging/admin_accesos.spec
# Requiere admin_accesos/frontend/dist (npm run build) antes de empaquetar.
# Usa su propio puerto (8090+), distinto del app principal (8080+).
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parent

# El frontend del admin se empaqueta como 'frontend/dist' porque su lanzador
# (admin_accesos/backend/main.resolve_static_dir) lo busca ahí dentro del bundle.
_datas = [(str(ROOT / "admin_accesos" / "frontend" / "dist"), "frontend/dist")]

# Credenciales Oracle: el .env de la raíz se codifica (ofuscado) y se embebe como
# '.envx', para que el .exe del admin sea autocontenido sin texto plano.
import os as _os, sys as _sys, tempfile as _tempfile
_sys.path.insert(0, str(ROOT))
_env_src = ROOT / ".env"
if _env_src.exists():
    from MACRO.funciones.funciones_generales import ofuscar_env
    _tmpd = _tempfile.mkdtemp(prefix="devolplus_env_")
    _envx = _os.path.join(_tmpd, ".envx")
    with open(_envx, "wb") as _fh:
        _fh.write(ofuscar_env(_env_src.read_text(encoding="utf-8")))
    _datas.append((_envx, "."))

_icon = ROOT / "MACRO" / "icon.ico"
_icon_arg = [str(_icon)] if _icon.exists() else None
if _icon.exists():
    _datas.append((str(_icon), "."))

# Versión del aplicativo: DEVOLPLUS_VERSION (build.py) o el archivo VERSION de la
# raíz; se embebe como 'VERSION' para que MACRO.version.get_version la lea.
_ver = _os.environ.get("DEVOLPLUS_VERSION", "").strip()
if not _ver:
    _vf = ROOT / "VERSION"
    _ver = _vf.read_text(encoding="utf-8").strip() if _vf.exists() else "0.0.0"
_ver_dir = _tempfile.mkdtemp(prefix="devolplus_ver_")
_ver_path = _os.path.join(_ver_dir, "VERSION")
with open(_ver_path, "w", encoding="utf-8") as _fh:
    _fh.write(_ver)
_datas.append((_ver_path, "."))

a = Analysis(
    [str(ROOT / "run_admin.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "win32timezone",
    ] + collect_submodules("oracledb")       # driver Oracle
      + collect_submodules("cryptography"),  # oracledb thin lo usa (kdf/hashes/ciphers)
    hookspath=[],
    runtime_hooks=[],
    excludes=["flet"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="DEVOL+ Admin",
    debug=False,
    strip=False,
    upx=False,
    console=False,  # True durante desarrollo (ver logs); poner False para release
    icon=_icon_arg,
)
