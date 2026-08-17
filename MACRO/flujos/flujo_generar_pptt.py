"""Armado del papel de trabajo por caso (modo demostración)."""

from __future__ import annotations

from MACRO.flujos._demo import adaptador, log_de, resultado


def cod_tip_sol_de(item) -> str:
    """Código de tipo de solicitud de un caso, como cadena de 2 dígitos."""
    valor = str((item or {}).get("cod_tip_sol", "")).strip()
    return valor.zfill(2) if valor.isdigit() else valor


def es_tipo_12(item) -> bool:
    """``True`` para las solicitudes de tipo 1 y 2, que llevan armado especial."""
    return cod_tip_sol_de(item) in {"01", "02"}


def procesar_generar_pptt(lista_num_doc, callback_progreso=None,
                          solicitar_password=None, solicitar_eleccion=None):
    """Genera el papel de trabajo de cada caso indicado."""
    log = log_de(callback_progreso)
    docs = [str(d) for d in (lista_num_doc or [])]
    ad = adaptador()
    oks, errores = [], []
    for i, num_doc in enumerate(docs, start=1):
        log(f"[{i}/{len(docs)}] Armando papel de trabajo de {num_doc}")
        r = ad.descargar(num_doc, "papel_trabajo")
        (oks if r.get("ok") else errores).append(num_doc)
    return resultado(
        not errores, f"{len(oks)} papel(es) de trabajo generado(s)", oks=oks,
        errores=[{"num_doc": d, "mensaje": "fallo simulado"} for d in errores],
    )


__all__ = ["procesar_generar_pptt", "es_tipo_12", "cod_tip_sol_de"]
