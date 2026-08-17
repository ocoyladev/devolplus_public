"""Carga y consulta de la tabla de casos (modo demostración)."""

from __future__ import annotations

from MACRO.flujos._demo import adaptador, filas_a_num_docs, log_de, resultado


def _df(filas):
    """Convierte una lista de registros a DataFrame; vacío si no hay filas."""
    import pandas as pd

    return pd.DataFrame(filas) if filas else pd.DataFrame()


def obtener_dataframe_actual():
    """Casos vigentes como DataFrame (lo que consume ``GET /api/datos/tabla``)."""
    return _df(adaptador().listar_casos(archivados=False))


def obtener_dataframe_archivo():
    """Casos archivados como DataFrame."""
    return _df(adaptador().listar_casos(archivados=True))


def cargar_asignacion_excel(callback_progreso=None, ruta=None):
    """Carga la asignación desde un Excel. En demo siembra el catálogo sintético."""
    from demo.seed import sembrar

    log = log_de(callback_progreso)
    log("Leyendo archivo de asignación…")
    insertados = sembrar()
    log(f"{insertados} caso(s) incorporado(s).")
    return resultado(True, f"{insertados} caso(s) cargado(s) desde el catálogo demo")


def cargar_sistema_legacy(callback_progreso=None, ruta=None):
    """Carga el reporte del sistema de consulta. En demo equivale a la asignación."""
    return cargar_asignacion_excel(callback_progreso=callback_progreso, ruta=ruta)


def verificar_y_conectar_servicios(
    callback_progreso=None, check_portal=True, check_workflow=True
):
    """Verifica la sesión contra los servicios remotos.

    Devuelve ``(sesion, cookie, ambos_ok)``: el tercer elemento evita que cada
    llamador tenga que recomponer la condición.
    """
    log = log_de(callback_progreso)
    log("Verificando servicios…")
    sesion, cookie = adaptador().verificar_servicios(
        check_portal=check_portal, check_workflow=check_workflow
    )
    return sesion, cookie, bool(sesion) and bool(cookie)


def procesar_descargas_bd(callback_progreso_ui=None, ids=None, omitir_planeamiento=False):
    """Procesa la cola de descargas pendientes registrada en la BD local."""
    from MACRO.database import obtener_descargas_pendientes_bd

    log = log_de(callback_progreso_ui)
    pendientes = obtener_descargas_pendientes_bd() or []
    if ids:
        pendientes = [p for p in pendientes if p.get("id") in set(ids)]
    ad = adaptador()
    oks: list[str] = []
    for i, p in enumerate(pendientes, start=1):
        num_doc = str(p.get("num_doc", ""))
        log(f"[{i}/{len(pendientes)}] {num_doc}")
        r = ad.descargar(num_doc, str(p.get("tipo_descarga") or "documento"))
        if r.get("ok"):
            oks.append(num_doc)
    return resultado(True, f"{len(oks)} descarga(s) procesada(s)", oks=oks)


def reintentar_descargas_pendientes(callback_progreso=None):
    """Reintenta las descargas que quedaron en estado pendiente."""
    return procesar_descargas_bd(callback_progreso_ui=callback_progreso)


def limpiar_cola_descargas(callback_progreso=None):
    """Vacía la cola de descargas pendientes."""
    from MACRO.database import limpiar_tabla_desc_bd

    limpiar_tabla_desc_bd()
    log_de(callback_progreso)("Cola de descargas vaciada.")
    return resultado(True, "Cola vaciada")


__all__ = [
    "obtener_dataframe_actual", "obtener_dataframe_archivo",
    "cargar_asignacion_excel", "cargar_sistema_legacy", "verificar_y_conectar_servicios",
    "procesar_descargas_bd", "reintentar_descargas_pendientes",
    "limpiar_cola_descargas",
]
