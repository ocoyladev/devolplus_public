"""Versión del aplicativo DEVOL+ (fuente única de verdad para el backend).

La versión vive en el archivo ``VERSION`` de la raíz del repo. Se resuelve así:

1. Variable de entorno ``DEVOLPLUS_VERSION`` (la fija ``build.py`` al empaquetar
   y la lee también la ``.spec``). Útil para sobreescribir sin tocar el archivo.
2. Archivo ``VERSION`` embebido en el bundle de PyInstaller (frozen) o el de la
   raíz del repo (desarrollo).
3. ``0.0.0`` como último recurso.

El frontend recibe la misma versión por separado (Vite ``define`` en build); ver
``frontend/vite.config.ts`` y ``admin_accesos/frontend/vite.config.ts``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_DEFAULT = "0.0.0"


def _version_file() -> Path:
    """Ruta al archivo ``VERSION``: en el bundle (frozen) o en la raíz del repo."""
    if getattr(sys, "frozen", False):  # empaquetado con PyInstaller
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent  # MACRO/ -> raíz
    return base / "VERSION"


def get_version() -> str:
    """Devuelve la versión del aplicativo (p. ej. ``"1.0.0"``)."""
    env = os.environ.get("DEVOLPLUS_VERSION")
    if env and env.strip():
        return env.strip()
    ruta = _version_file()
    try:
        contenido = ruta.read_text(encoding="utf-8").strip()
        if contenido:
            return contenido
    except OSError:
        pass
    return _DEFAULT
