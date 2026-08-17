"""Generación de cartas y resoluciones a partir de plantillas (modo demostración)."""

from __future__ import annotations

from MACRO.flujos._demo import adaptador, log_de, resultado


def listar_modelos(tipo: str) -> list[str]:
    """Plantillas .docx disponibles para ``tipo`` (``carta`` | ``ri``)."""
    return adaptador().listar_modelos(tipo)


def generar_carta_caso(row, modelos, plazo, callback_progreso=None, archivo=False) -> dict:
    """Genera la carta del caso combinando la plantilla elegida con sus datos."""
    log = log_de(callback_progreso)
    num_doc = str((row or {}).get("num_doc", ""))
    modelo = (modelos[0] if isinstance(modelos, (list, tuple)) and modelos else modelos) or ""
    log(f"Generando carta de {num_doc} (plazo {plazo})…")
    r = adaptador().generar_documento(num_doc, "carta", str(modelo))
    return resultado(r.get("ok", False), r.get("mensaje", ""), ruta=r.get("ruta"))


def generar_ri_caso(row, modelo, num_ri, callback_progreso=None) -> dict:
    """Genera la resolución del caso a partir de la plantilla ``modelo``."""
    log = log_de(callback_progreso)
    num_doc = str((row or {}).get("num_doc", ""))
    log(f"Generando resolución {num_ri} de {num_doc}…")
    r = adaptador().generar_documento(num_doc, "ri", str(modelo))
    return resultado(r.get("ok", False), r.get("mensaje", ""), ruta=r.get("ruta"), num_ri=num_ri)


__all__ = ["listar_modelos", "generar_carta_caso", "generar_ri_caso"]
