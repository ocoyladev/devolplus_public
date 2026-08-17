"""Utilidades compartidas por los flujos en modo demostración."""

from __future__ import annotations

from typing import Any

from MACRO.adapters import get_adapter


def adaptador():
    """Adaptador activo. Se resuelve por llamada para permitir override en tests."""
    return get_adapter()


def log_de(callback_progreso: Any):
    """Normaliza el callback de progreso a una función ``log(mensaje)``."""

    def log(mensaje: str) -> None:
        if callback_progreso is None:
            return
        try:
            callback_progreso(mensaje)
        except TypeError:
            try:
                callback_progreso(0, 0, mensaje)
            except TypeError:
                pass

    return log


def resultado(ok: bool = True, mensaje: str = "", **extra) -> dict:
    """Forma canónica de retorno de los flujos: ``{ok, mensaje, oks, errores}``."""
    base = {"ok": ok, "mensaje": mensaje, "oks": [], "errores": []}
    base.update(extra)
    return base


def filas_a_num_docs(filas) -> list[str]:
    """Extrae los números de documento de una lista de filas o de strings."""
    docs: list[str] = []
    for f in filas or []:
        if isinstance(f, dict):
            valor = f.get("num_doc") or f.get("N° DOC.") or ""
        else:
            valor = f
        if valor:
            docs.append(str(valor))
    return docs
