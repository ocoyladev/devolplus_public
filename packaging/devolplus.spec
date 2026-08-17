# -*- mode: python ; coding: utf-8 -*-
# Spec de PyInstaller para DEVOL+ (app web local). Construir en Windows:
#   pyinstaller packaging/devolplus.spec
# Requiere que frontend/dist exista (npm run build) antes de empaquetar.
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parent

_datas = [(str(ROOT / "frontend" / "dist"), "frontend/dist")]

# Paquete de automatización SISTEMA_LEGACY vendorizado (REF/Tiempos, Antecedentes). Se
# incluye como DATOS (no como módulos) porque flujo_sistema_legacy lo importa de forma
# dinámica insertando su carpeta en sys.path; PyInstaller no lo detectaría solo.
# En el bundle queda en <_MEIPASS>/automatizaciones (ver flujo_sistema_legacy._automatizaciones_dir).
_automat = ROOT / "MACRO" / "automatizaciones"
if _automat.exists():
    _datas.append((str(_automat), "automatizaciones"))

# Credenciales: se CODIFICAN (ofuscadas) y se embeben como '.envx', para que el
# .exe sea autocontenido sin dejar las credenciales en texto plano. La app lo
# decodifica al arrancar (cargar_env). Recomendado: que el usuario Oracle sea de
# MÍNIMOS privilegios (solo las tablas de acceso).
#
# Se FUSIONAN dos archivos porque las credenciales viven repartidas:
#   * ROOT/.env      -> Oracle (ORACLE_*) del control de acceso.
#   * ROOT/MACRO/.env -> SQL Server (DB_*), Portal, Workflow, SharePoint.
# Si solo se embebiera ROOT/.env, el .exe quedaría SIN DB_* y toda consulta a la
# BD interna volvería vacía ("No se encontraron datos"). Orden: MACRO/.env
# primero y ROOT/.env después, para que la raíz gane ante claves repetidas.
import os as _os, sys as _sys, tempfile as _tempfile
_sys.path.insert(0, str(ROOT))
_env_parts = []
for _p in (ROOT / "MACRO" / ".env", ROOT / ".env"):
    if _p.exists():
        _env_parts.append(_p.read_text(encoding="utf-8"))
if _env_parts:
    from MACRO.funciones.funciones_generales import ofuscar_env
    _merged_env = "\n".join(_env_parts)
    _tmpd = _tempfile.mkdtemp(prefix="devolplus_env_")
    _envx = _os.path.join(_tmpd, ".envx")
    with open(_envx, "wb") as _fh:
        _fh.write(ofuscar_env(_merged_env))
    _datas.append((_envx, "."))

# Ícono del ejecutable (reutilizado de las builds Flet: MACRO/icon.ico). Se pasa
# como lista (misma forma que DEVOL5/6.spec, que sí incrustaban el ícono en el
# .exe) y se empaqueta también como dato por si la app lo usa como ícono de
# ventana. NOTA: si tras recompilar el Explorador de Windows sigue mostrando el
# ícono viejo/en blanco del .exe, suele ser la caché de íconos del sistema
# (el ícono sí queda incrustado: la ventana/barra de tareas lo muestran).
_icon = ROOT / "MACRO" / "icon.ico"
_icon_arg = [str(_icon)] if _icon.exists() else None
if _icon.exists():
    _datas.append((str(_icon), "."))

# Versión del aplicativo: se resuelve DEVOLPLUS_VERSION (la fija build.py) o, en
# su defecto, el archivo VERSION de la raíz; y se embebe como 'VERSION' para que
# MACRO.version.get_version la lea en el .exe y la registre en cada logueo.
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
    [str(ROOT / "run_web.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        # pywin32 importa win32timezone de forma diferida al convertir valores
        # fecha/hora devueltos por COM (p. ej. leer una celda de fecha de Excel,
        # como N3 -> fecha_doc_macro). PyInstaller no lo detecta solo y sin él
        # falla con ModuleNotFoundError, dejando fecha_doc_macro vacío en el REF.
        "win32timezone",
    ] + collect_submodules("oracledb")       # driver Oracle (control de acceso)
      + collect_submodules("cryptography")   # oracledb thin lo usa (kdf/hashes/ciphers)
      # Automatización SISTEMA_LEGACY (import dinámico): PyInstaller no ve pywinauto/pyautogui
      # ni comtypes (backend UIA de pywinauto), así que se fuerzan sus submódulos.
      + collect_submodules("pywinauto")
      + collect_submodules("pyautogui")
      + collect_submodules("comtypes"),
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
    name="DEVOL+",
    debug=False,
    strip=False,
    upx=False,
    console=False,  # True durante desarrollo (ver logs); poner False para release
    icon=_icon_arg,
)
