"""Descarga de artefactos por caso y en masa (modo demostración)."""

from __future__ import annotations

from MACRO.flujos._demo import adaptador, filas_a_num_docs, log_de, resultado


def _descargar(row, tipo, callback_progreso=None, **extra) -> dict:
    log = log_de(callback_progreso)
    num_doc = str((row or {}).get("num_doc", ""))
    log(f"Descargando {tipo} de {num_doc}…")
    r = adaptador().descargar(num_doc, tipo, progreso=callback_progreso)
    return resultado(r.get("ok", False), r.get("mensaje", ""), ruta=r.get("ruta"), **extra)


def _masivo(filas, tipo, callback_progreso=None) -> dict:
    log = log_de(callback_progreso)
    docs = filas_a_num_docs(filas)
    ad = adaptador()
    oks, errores = [], []
    for i, num_doc in enumerate(docs, start=1):
        log(f"[{i}/{len(docs)}] {tipo} de {num_doc}")
        r = ad.descargar(num_doc, tipo)
        (oks if r.get("ok") else errores).append(num_doc)
    return resultado(
        not errores, f"{len(oks)} de {len(docs)} descargado(s)", oks=oks,
        errores=[{"num_doc": d, "mensaje": "fallo simulado"} for d in errores],
    )


def descargar_ri_caso(row, ri_valor=None, callback_progreso=None, archivo=False):
    return _descargar(row, "ri", callback_progreso, ri=ri_valor)


def descargar_cartas_caso(row, cartas_valor=None, callback_progreso=None, archivo=False):
    return _descargar(row, "cartas", callback_progreso, cartas=cartas_valor)


def descargar_exp_electronico_caso(row, callback_progreso=None):
    return _descargar(row, "expediente_electronico", callback_progreso)


def descargar_3uit_caso(row, num_formulario=None, callback_progreso=None):
    return _descargar(row, "deduccion_3uit", callback_progreso, formulario=num_formulario)


def descargar_planeamiento_caso(row, ruc, callback_progreso=None):
    return _descargar(row, "planeamiento", callback_progreso, ruc=ruc)


def descargar_por_ejercicios_caso(row, count, callback_progreso=None):
    return _descargar(row, "ejercicios", callback_progreso, ejercicios=count)


def descargar_ri_masivo(filas, archivo=False, callback_progreso=None):
    return _masivo(filas, "ri", callback_progreso)


def descargar_cartas_masivo(filas, archivo=False, callback_progreso=None):
    return _masivo(filas, "cartas", callback_progreso)


def agregar_numeracion_cartas(filas, callback_progreso=None):
    """Numera correlativamente las cartas de las filas indicadas."""
    log = log_de(callback_progreso)
    docs = filas_a_num_docs(filas)
    for i, num_doc in enumerate(docs, start=1):
        log(f"Numerando carta {i:03d} de {num_doc}")
    return resultado(True, f"{len(docs)} carta(s) numerada(s)", oks=docs)


__all__ = [
    "descargar_ri_caso", "descargar_cartas_caso", "descargar_exp_electronico_caso",
    "descargar_3uit_caso", "descargar_planeamiento_caso", "descargar_por_ejercicios_caso",
    "descargar_ri_masivo", "descargar_cartas_masivo", "agregar_numeracion_cartas",
]
