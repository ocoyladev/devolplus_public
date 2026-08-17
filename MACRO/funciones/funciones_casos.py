"""Helpers de ubicación de carpetas de casos (independientes de la GUI).

Extraído de ``ui.py`` para que la capa web (y cualquier flujo) pueda resolver
la carpeta de un caso sin depender de Flet.
"""
from __future__ import annotations

import os
import subprocess
import sys

from ..config import DEFAULT_PATH_DESCARGAS
from ..database import obtener_config


def abrir_en_sistema(path: str) -> None:
    """Abre un archivo/carpeta con la app por defecto del SO.

    Se ejecuta del lado del servidor, que en este despliegue es la propia PC del
    usuario, replicando el ``os.startfile`` de los handlers Flet.
    """
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]  # noqa: PLC0415
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def get_case_folder(row: dict) -> str:
    """Carpeta asignada al caso, considerando la lógica OF_SINGLE / OF_MULTIPLE."""
    carpeta_descargas = obtener_config("PATH_DESCARGAS", DEFAULT_PATH_DESCARGAS)
    of_dev = str(row.get("of_devolucion", "")).strip()
    ruc = str(row.get("ruc", "") or row.get("num_ruc", "")).strip()
    nombre = str(row.get("nombre", "") or row.get("ddp_nombre", "")).strip()[:40]
    num_doc = str(row.get("num_doc", "")).strip()

    nombre_safe = "".join(
        c for c in nombre if c.isalnum() or c in (" ", "_", "-")
    ).strip()

    base_folder_name = f"{of_dev}_{ruc}_{nombre_safe}"

    if row.get("is_of_multiple", False):
        return os.path.join(carpeta_descargas, base_folder_name, num_doc)
    return os.path.join(carpeta_descargas, base_folder_name)


def get_archive_folder(row: dict) -> str:
    """Carpeta del caso dentro de PATH_ARCHIVO (cuando está archivado).

    archivar_casos mueve la carpeta del caso a ``PATH_ARCHIVO/<basename>``; esta
    función reconstruye esa ruta para abrir la carpeta desde la vista de archivo.
    """
    from ..config import DEFAULT_PATH_ARCHIVO

    path_archivo = obtener_config("PATH_ARCHIVO", DEFAULT_PATH_ARCHIVO)
    return os.path.join(path_archivo, os.path.basename(get_case_folder(row)))
