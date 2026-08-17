"""Verificación y envío de expedientes al repositorio documental (demo)."""

from __future__ import annotations

from collections.abc import Callable

from MACRO.flujos._demo import adaptador, log_de, resultado


def echasqui_subido(denom: str, docs: list[dict]) -> bool:
    """``True`` si ``denom`` ya figura entre los documentos del repositorio."""
    objetivo = (denom or "").strip().lower()
    return any(objetivo == str(d.get("nombre", "")).strip().lower() for d in docs or [])


def verificar_exp_echasqui(
    num_docs: list[str], callback_progreso: Callable[[str], None] | None = None
) -> dict:
    """Comprueba, por caso, si el expediente ya fue enviado al repositorio."""
    log = log_de(callback_progreso)
    items = []
    for i, num_doc in enumerate(num_docs or [], start=1):
        log(f"[{i}/{len(num_docs or [])}] Verificando {num_doc}")
        # En demo alternamos el estado para que la UI muestre ambos caminos.
        subido = (i % 2) == 0
        items.append({
            "num_doc": str(num_doc),
            "estado": "subido" if subido else "pendiente",
            "denominacion": f"EXP-{num_doc}",
        })
    pendientes = [i for i in items if i["estado"] == "pendiente"]
    return resultado(
        True, f"{len(pendientes)} pendiente(s) de {len(items)}",
        items=items, pendientes=pendientes,
    )


def subir_echasqui_pendientes(
    items: list[dict], callback_progreso: Callable[[str], None] | None = None
) -> dict:
    """Envía al repositorio los expedientes marcados como pendientes."""
    log = log_de(callback_progreso)
    oks = []
    for i, item in enumerate(items or [], start=1):
        num_doc = str(item.get("num_doc", ""))
        log(f"[{i}/{len(items or [])}] Subiendo {num_doc}")
        adaptador().descargar(num_doc, "echasqui")
        oks.append(num_doc)
    return resultado(True, f"{len(oks)} expediente(s) enviado(s)", oks=oks)


__all__ = ["echasqui_subido", "verificar_exp_echasqui", "subir_echasqui_pendientes"]
