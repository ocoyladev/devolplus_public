"""Descargas por lote desde el sistema de consulta legacy (modo demostración).

En el despliegue real este flujo automatiza una aplicación de escritorio; aquí
se resuelve contra el adaptador demo, sin ninguna dependencia de UI.
"""

from __future__ import annotations

from MACRO.flujos._demo import adaptador, filas_a_num_docs, log_de, resultado


def _agrupar_por_of(filas: list[dict]) -> list[tuple[str, dict]]:
    """Agrupa las filas por orden de devolución, conservando la primera de cada una."""
    vistos: dict[str, dict] = {}
    for f in filas or []:
        of_dev = str(f.get("of_devolucion") or f.get("OF.") or "")
        vistos.setdefault(of_dev, f)
    return sorted(vistos.items())


def verificar_pendientes_rsirat(tipo: str, filas) -> dict:
    """Indica qué órdenes aún no tienen el reporte ``tipo`` descargado.

    Respuesta síncrona que consume el diálogo de confirmación:
    ``{tipo, total, pendientes, casos}`` donde ``pendientes`` es el conteo.
    """
    grupos = _agrupar_por_of(filas)
    casos = []
    for i, (of_dev, fila) in enumerate(grupos):
        # En demo se considera pendiente una de cada tres órdenes.
        pendiente = (i % 3) == 0
        casos.append({
            "of_devolucion": of_dev,
            "num_doc": str(fila.get("num_doc", "")),
            "pendiente": pendiente,
            "motivo": "sin reporte descargado" if pendiente else "",
        })
    return {
        "tipo": tipo,
        "total": len(casos),
        "pendientes": sum(1 for c in casos if c["pendiente"]),
        "casos": casos,
    }


def _descargar_lote(filas, tipo, callback_progreso=None):
    log = log_de(callback_progreso)
    grupos = _agrupar_por_of(filas)
    ad = adaptador()
    oks = []
    for i, (of_dev, fila) in enumerate(grupos, start=1):
        log(f"[{i}/{len(grupos)}] {tipo} de la orden {of_dev}")
        r = ad.descargar(str(fila.get("num_doc", "")), tipo)
        if r.get("ok"):
            oks.append(of_dev)
    return resultado(True, f"{len(oks)} orden(es) procesada(s)", oks=oks)


def descargar_ref_tiempos_rsirat(filas, callback_progreso=None):
    """Descarga el reporte de referencia y tiempos por orden."""
    return _descargar_lote(filas, "ref_tiempos", callback_progreso)


def descargar_antecedentes_rsirat(filas, callback_progreso=None):
    """Descarga los antecedentes por orden."""
    return _descargar_lote(filas, "antecedentes", callback_progreso)


__all__ = [
    "verificar_pendientes_rsirat", "descargar_ref_tiempos_rsirat",
    "descargar_antecedentes_rsirat",
]
