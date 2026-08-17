"""Carga masiva de expedientes electrónicos (modo demostración)."""

from __future__ import annotations

from MACRO.flujos._demo import adaptador, log_de, resultado


def cargar_expedientes_electronicos(lista_docs, ejecutar_firma_auto=False, callback_progreso=None):
    """Sube los expedientes de los casos indicados al portal documental."""
    log = log_de(callback_progreso)
    docs = [str(d) for d in (lista_docs or [])]
    ad = adaptador()
    oks = []
    for i, num_doc in enumerate(docs, start=1):
        log(f"[{i}/{len(docs)}] Cargando expediente de {num_doc}")
        if ad.descargar(num_doc, "carga_expediente").get("ok"):
            oks.append(num_doc)
    if ejecutar_firma_auto:
        log("Firma automática: omitida en modo demo (requiere certificado local).")
    return resultado(True, f"{len(oks)} expediente(s) cargado(s)", oks=oks)


__all__ = ["cargar_expedientes_electronicos"]
