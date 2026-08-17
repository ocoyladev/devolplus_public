"""Autorización de casos: parseo de entradas, conflictos y aplicación (demo)."""

from __future__ import annotations

from datetime import date, datetime

from MACRO.flujos._demo import adaptador, log_de, resultado


def _a_float(valor) -> float:
    try:
        return float(str(valor).replace(",", "").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def _parsear_entrada_fecha(s):
    """Acepta DD/MM/YYYY o DD-MM-YYYY; devuelve ``date`` o ``None``."""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except (TypeError, ValueError):
            continue
    return None


def parsear_entradas_autorizar(lines, hoy=None, log=None):
    """Convierte líneas ``num_doc;resultado;monto;fecha`` en decisiones.

    Formato tolerante: separador ``;`` o tabulación, campos sobrantes ignorados.
    Devuelve ``(decisiones, errores)``.
    """
    hoy = hoy or date.today()
    decisiones, errores = [], []
    for n, linea in enumerate(lines or [], start=1):
        texto = str(linea).strip()
        if not texto:
            continue
        partes = [p.strip() for p in texto.replace("\t", ";").split(";")]
        if not partes or not partes[0]:
            errores.append({"linea": n, "mensaje": "Falta el número de documento"})
            continue
        decisiones.append({
            "num_doc": partes[0],
            "resultado": partes[1] if len(partes) > 1 else "",
            "monto": _a_float(partes[2]) if len(partes) > 2 else 0.0,
            "fecha": _parsear_entrada_fecha(partes[3]) if len(partes) > 3 else hoy,
        })
    return decisiones, errores


def evaluar_conflicto_autorizar(resultado_caso, c89, c65) -> bool:
    """``True`` si el resultado declarado contradice las casillas 89/65."""
    autoriza = str(resultado_caso or "").lower().startswith("aut")
    return autoriza and _a_float(c89) <= 0 and _a_float(c65) <= 0


def evaluar_conflicto_c64(resultado_caso, c64) -> bool:
    """``True`` si el resultado declarado contradice la casilla 64."""
    autoriza = str(resultado_caso or "").lower().startswith("aut")
    return autoriza and _a_float(c64) <= 0


def prechequear_autorizar(lines):
    """Valida las entradas antes de aplicarlas y reporta conflictos."""
    decisiones, errores = parsear_entradas_autorizar(lines)
    conflictos = [d for d in decisiones if not d["resultado"]]
    return {
        "ok": not errores,
        "decisiones": decisiones,
        "errores": errores,
        "conflictos": conflictos,
        "mensaje": f"{len(decisiones)} decisión(es) leída(s), {len(errores)} error(es)",
    }


def _decisiones_a_aplicar(decisiones):
    """Filtra las decisiones confirmadas por el usuario."""
    return [d for d in (decisiones or []) if d.get("aplicar", True)]


def _decisiones_c64_a_aplicar(decisiones_c64):
    """Ídem para el circuito de la casilla 64."""
    return [d for d in (decisiones_c64 or []) if d.get("aplicar", True)]


def autorizar_casos(lines, decisiones=None, decisiones_c64=None, callback_progreso=None):
    """Aplica las decisiones de autorización sobre los casos indicados."""
    log = log_de(callback_progreso)
    if decisiones is None:
        decisiones, _ = parsear_entradas_autorizar(lines)
    aplicar = _decisiones_a_aplicar(decisiones) + _decisiones_c64_a_aplicar(decisiones_c64)
    log(f"Aplicando {len(aplicar)} decisión(es)…")
    r = adaptador().autorizar(aplicar, progreso=callback_progreso)
    return resultado(
        r.get("ok", False), r.get("mensaje", ""),
        oks=[d["num_doc"] for d in aplicar],
    )


def _texto_celda(v) -> str:
    return "" if v is None else str(v).strip()


def _filas_anexo(df_final) -> list[dict]:
    """Filas que componen el anexo de devoluciones a partir del DataFrame final."""
    if df_final is None or getattr(df_final, "empty", True):
        return []
    columnas = ["num_doc", "num_ruc", "ddp_nombre", "mto_solicitado", "resultado"]
    filas = []
    for reg in df_final.to_dict(orient="records"):
        filas.append({c: _texto_celda(reg.get(c)) for c in columnas})
    return filas


def generar_anexo_devoluciones(filas: list[dict], carpeta: str) -> str | None:
    """Escribe el anexo en ``carpeta`` como CSV. Devuelve la ruta o ``None``."""
    import csv
    from pathlib import Path

    if not filas:
        return None
    destino = Path(carpeta) / "anexo_devoluciones.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    return str(destino)


__all__ = [
    "parsear_entradas_autorizar", "evaluar_conflicto_autorizar", "evaluar_conflicto_c64",
    "prechequear_autorizar", "autorizar_casos", "generar_anexo_devoluciones",
]
