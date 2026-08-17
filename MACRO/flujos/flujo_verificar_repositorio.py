"""Verificación y envío de expedientes al repositorio documental (demo)."""

from __future__ import annotations

from collections.abc import Callable

from MACRO.flujos._demo import adaptador, log_de, resultado


def repositorio_subido(denom: str, docs: list[dict]) -> bool:
    """``True`` si ``denom`` ya figura entre los documentos del repositorio."""
    objetivo = (denom or "").strip().lower()
    return any(objetivo == str(d.get("nombre", "")).strip().lower() for d in docs or [])


def verificar_exp_repositorio(
    num_docs: list[str], callback_progreso: Callable[[str], None] | None = None
) -> dict:
    """Comprueba, por caso, qué documentos ya figuran en el repositorio.

    Devuelve ``{"casos": [...]}`` con la forma que espera ``CasoRepositorio``:
    cada caso lleva su lista de documentos y el estado de cada uno.
    """
    log = log_de(callback_progreso)
    ad = adaptador()
    por_num_doc = {str(c.get("num_doc")): c for c in ad.listar_casos()}

    casos = []
    docs = [str(d) for d in (num_docs or [])]
    for i, num_doc in enumerate(docs, start=1):
        log(f"[{i}/{len(docs)}] Verificando {num_doc}")
        fila = por_num_doc.get(num_doc, {})
        # En demo se alterna el estado para que la UI muestre ambos caminos.
        subido = (i % 2) == 0
        casos.append({
            "num_doc": num_doc,
            "num_dev": str(fila.get("num_dev", "")),
            "num_ruc": str(fila.get("num_ruc", "")),
            "nombre": str(fila.get("ddp_nombre", "")),
            "tipo_exp": "electronico" if str(fila.get("cod_for")) == "1649" else "fisico",
            "repositorios": [{
                "denom": f"EXP-{num_doc}",
                "clasificacion": "expediente",
                "estado": "registrado" if subido else "pendiente",
                "subible": not subido,
            }],
            "sin_repositorio": False,
            "error": "",
        })
    return {"casos": casos}


def subir_repositorio_pendientes(
    items: list[dict], callback_progreso: Callable[[str], None] | None = None
) -> dict:
    """Envía al repositorio los expedientes marcados como pendientes."""
    log = log_de(callback_progreso)
    ad = adaptador()
    oks = []
    for i, item in enumerate(items or [], start=1):
        num_doc = str(item.get("num_doc", ""))
        denom = str(item.get("denom", "")) or f"EXP-{num_doc}"
        log(f"[{i}/{len(items or [])}] Subiendo {denom}")
        ad.descargar(num_doc, "repositorio")
        oks.append(num_doc)
    return resultado(True, f"{len(oks)} documento(s) enviado(s)", oks=oks)


__all__ = ["repositorio_subido", "verificar_exp_repositorio", "subir_repositorio_pendientes"]
