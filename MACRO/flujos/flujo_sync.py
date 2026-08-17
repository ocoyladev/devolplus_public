"""Sincronización de la tabla local con el origen remoto (modo demostración)."""

from __future__ import annotations

from MACRO.flujos._demo import adaptador, log_de, resultado


def actualizar_desde_macros(callback_progreso=None, num_docs=None):
    """Refresca los casos indicados (o todos) desde el back-office."""
    log = log_de(callback_progreso)
    casos = adaptador().listar_casos()
    objetivo = [str(d) for d in (num_docs or [])] or [c.get("num_doc") for c in casos]
    for i, num_doc in enumerate(objetivo, start=1):
        log(f"[{i}/{len(objetivo)}] Sincronizando {num_doc}")
    return resultado(True, f"{len(objetivo)} caso(s) sincronizado(s)", oks=list(objetivo))


def actualizar_segun_bd_remota(callback_progreso=None):
    """Cruza la tabla local contra la base remota de referencia."""
    log = log_de(callback_progreso)
    log("Contrastando con la base remota…")
    casos = adaptador().listar_casos()
    return resultado(True, f"{len(casos)} caso(s) contrastado(s)")


__all__ = ["actualizar_desde_macros", "actualizar_segun_bd_remota"]
