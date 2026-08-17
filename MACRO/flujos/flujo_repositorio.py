"""Descarga de expedientes del repositorio documental (modo demostración)."""

from __future__ import annotations

from MACRO.flujos._demo import adaptador, log_de, resultado


def descargar_expedientes_caso(row, expedientes, callback_progreso=None):
    """Descarga los expedientes seleccionados de un caso."""
    log = log_de(callback_progreso)
    num_doc = str((row or {}).get("num_doc", ""))
    ad = adaptador()
    oks = []
    lista = list(expedientes or [])
    for i, exp in enumerate(lista, start=1):
        log(f"[{i}/{len(lista)}] Expediente {exp} de {num_doc}")
        r = ad.descargar(num_doc, f"expediente_{exp}")
        if r.get("ok"):
            oks.append(str(exp))
    return resultado(True, f"{len(oks)} expediente(s) descargado(s)", oks=oks)


__all__ = ["descargar_expedientes_caso"]
