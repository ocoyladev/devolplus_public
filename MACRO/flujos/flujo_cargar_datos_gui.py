"""Alta de casos desde una lista de documentos (modo demostración)."""

from __future__ import annotations

from MACRO.flujos._demo import adaptador, log_de, resultado


def cargar_datos_desde_lista(lista_documentos: list, callback_progreso=None):
    """Da de alta los casos indicados por número de documento."""
    docs = [str(d).strip() for d in (lista_documentos or []) if str(d).strip()]
    r = adaptador().cargar_casos(docs, progreso=callback_progreso)
    return resultado(
        r.get("ok", False), r.get("mensaje", ""),
        oks=[d for d in docs if d not in set(r.get("no_encontrados", []))],
        errores=[{"num_doc": d, "mensaje": "no existe en el catálogo demo"}
                 for d in r.get("no_encontrados", [])],
    )


def cargar_autorizacion_ri(ruta, callback_progreso=None):
    """Lee un archivo de autorizaciones de resolución. En demo no lee disco."""
    log = log_de(callback_progreso)
    log(f"Leyendo autorizaciones desde {ruta}…")
    return resultado(True, "Modo demo: no se procesan archivos externos", oks=[])


__all__ = ["cargar_datos_desde_lista", "cargar_autorizacion_ri"]
