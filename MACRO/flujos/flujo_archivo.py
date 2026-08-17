"""Archivado y recuperación de casos (modo demostración)."""

from __future__ import annotations

from MACRO.flujos._demo import adaptador, log_de, resultado


def archivar_casos(lista_num_doc, callback_progreso=None) -> dict:
    """Mueve los casos indicados a la tabla de archivados."""
    log = log_de(callback_progreso)
    docs = [str(d) for d in (lista_num_doc or [])]
    log(f"Archivando {len(docs)} caso(s)…")
    r = adaptador().archivar(docs, progreso=callback_progreso)
    return resultado(r.get("ok", False), r.get("mensaje", ""), oks=docs if r.get("ok") else [])


def recuperar_casos(lista_num_doc, callback_progreso=None) -> dict:
    """Devuelve casos archivados a la tabla vigente."""
    from MACRO.database import recuperar_casos_db

    log = log_de(callback_progreso)
    docs = [str(d) for d in (lista_num_doc or [])]
    log(f"Recuperando {len(docs)} caso(s)…")
    try:
        recuperar_casos_db(docs)
    except Exception as exc:  # noqa: BLE001
        return resultado(False, f"No se pudo recuperar: {exc}")
    return resultado(True, f"{len(docs)} caso(s) recuperado(s)", oks=docs)


__all__ = ["archivar_casos", "recuperar_casos"]
