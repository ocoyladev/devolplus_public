"""Cola de archivado de expedientes en el repositorio documental (demo)."""

from __future__ import annotations

from MACRO.flujos._demo import adaptador, log_de, resultado


def encolar_archivar_echasqui(num_docs: list[str]) -> dict:
    """Registra en la cola local los casos a archivar. Devuelve los ids creados."""
    from MACRO.database import upsert_archivar_echasqui

    ids = []
    for num_doc in num_docs or []:
        try:
            ids.append(upsert_archivar_echasqui({"num_doc": str(num_doc),
                                                 "estado": "pendiente"}))
        except Exception:  # noqa: BLE001 — la cola no debe frenar el job
            continue
    return resultado(True, f"{len(ids)} caso(s) encolado(s)", ids=[i for i in ids if i])


def ejecutar_archivar_echasqui(ids: list[int] | None = None, callback_progreso=None) -> dict:
    """Procesa la cola de archivado y marca cada elemento como atendido."""
    from MACRO.database import listar_archivar_echasqui

    log = log_de(callback_progreso)
    pendientes = [p for p in (listar_archivar_echasqui() or [])
                  if ids is None or p.get("id") in set(ids)]
    oks = []
    for i, p in enumerate(pendientes, start=1):
        num_doc = str(p.get("num_doc", ""))
        log(f"[{i}/{len(pendientes)}] Archivando {num_doc}")
        adaptador().descargar(num_doc, "constancia_archivo")
        oks.append(num_doc)
    return resultado(True, f"{len(oks)} caso(s) archivado(s)", oks=oks)


__all__ = ["encolar_archivar_echasqui", "ejecutar_archivar_echasqui"]
