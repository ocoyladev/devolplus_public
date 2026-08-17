"""Validación del archivo de casos y subsanación de faltantes (modo demostración).

Conserva las mismas costuras que el despliegue real —``obtener_datos_incluye_archivo``,
``verificar_y_conectar_servicios``, ``num_docs_archivados``, ``ofs_all_electronicas``
y ``_evaluar_un_caso`` son atributos de módulo— para que la orquestación
(recorrido, emisión de progreso, agregación) se pueda probar sustituyéndolas.
"""

from __future__ import annotations

from pathlib import Path

from MACRO.flujos._demo import adaptador, log_de, resultado
from MACRO.flujos.flujo_asignacion_excel import verificar_y_conectar_servicios

# Comprobaciones evaluadas por caso antes de dar el archivo por conforme.
CHECKS = ("carpeta", "resolucion", "cargo_notificacion", "expediente")


def obtener_datos_incluye_archivo(num_docs):
    """DataFrame de los casos indicados, incluyendo los ya archivados."""
    import pandas as pd

    objetivo = {str(d) for d in (num_docs or [])}
    filas = [c for c in adaptador().listar_casos()
             if not objetivo or str(c.get("num_doc")) in objetivo]
    return pd.DataFrame(filas) if filas else pd.DataFrame()


def num_docs_archivados(num_docs) -> list[str]:
    """Subconjunto de ``num_docs`` que ya está archivado."""
    archivados = {str(c.get("num_doc")) for c in adaptador().listar_casos(archivados=True)}
    return [str(d) for d in (num_docs or []) if str(d) in archivados]


def ofs_all_electronicas(ofs: list[str]) -> set[str]:
    """Órdenes cuyos expedientes son todos electrónicos."""
    return {str(of) for of in (ofs or []) if str(of).endswith("E")}


def _row_get(row, *claves, default=""):
    for c in claves:
        if isinstance(row, dict) and row.get(c) not in (None, ""):
            return row[c]
    return default


def _fila_de(num_doc):
    """Busca la fila del caso en la tabla vigente."""
    for c in adaptador().listar_casos():
        if str(c.get("num_doc")) == str(num_doc):
            return c
    return None


def resolver_carpeta_caso(row) -> tuple[str, str, bool, bool]:
    """Devuelve ``(raiz, carpeta_trabajo, existe, es_multiple)``."""
    from MACRO.funciones.funciones_casos import get_case_folder

    trabajo = get_case_folder(row or {})
    raiz = str(Path(trabajo).parent)
    of_dev = str(_row_get(row, "of_devolucion", "OF."))
    return raiz, trabajo, Path(trabajo).is_dir(), of_dev.count("-") > 1


def _evaluar_un_caso(sesion, row, docs_archivados, ofs_elec, log) -> dict:
    """Evalúa las comprobaciones de un caso y devuelve su ficha de validación."""
    del sesion, docs_archivados, ofs_elec, log
    num_doc = str(_row_get(row, "num_doc"))
    _raiz, trabajo, existe, es_multiple = resolver_carpeta_caso(row)
    alertas = [] if existe else [{
        "codigo": "carpeta_ausente",
        "severidad": "alta",
        "mensaje": "La carpeta del caso no existe",
        "accion": "crear_carpeta",
    }]
    return {
        "num_doc": num_doc,
        "num_ruc": str(_row_get(row, "num_ruc", "ruc")),
        "nombre": str(_row_get(row, "ddp_nombre", "nombre")),
        "of_devolucion": str(_row_get(row, "of_devolucion")),
        "cod_tip_sol": str(_row_get(row, "cod_tip_sol")),
        "is_of_multiple": es_multiple,
        "carpeta_existe": existe,
        "paso_pptt": existe,
        "insumo_final": {"completo": existe, "faltantes": [], "puede_foliar": existe},
        "exp_echasqui": {"registrado": existe, "valor": trabajo},
        "echasquis": [],
        "carga_1649": {"aplica": str(_row_get(row, "cod_for")) == "1649"},
        "indispensables": {"raiz": [], "subcarpetas": {}},
        "alertas": alertas,
        "nivel": "ok" if existe else "alerta",
    }


def validar_casos(num_docs: list[str], callback_progreso=None) -> dict:
    """Evalúa las comprobaciones de archivo sobre cada caso.

    Emite ``{done, total, etiqueta}`` antes de empezar y tras cada caso, para que
    la UI muestre avance en lotes grandes (el endpoint es síncrono).
    """
    docs = [str(d) for d in (num_docs or [])]
    total = len(docs)

    def avisar(done: int, etiqueta: str) -> None:
        if callback_progreso is not None:
            callback_progreso({"done": done, "total": total, "etiqueta": etiqueta})

    df = obtener_datos_incluye_archivo(docs)
    sesion, *_ = verificar_y_conectar_servicios(check_portal=True, check_workflow=False)
    archivados = num_docs_archivados(docs)
    filas = df.to_dict(orient="records") if not getattr(df, "empty", True) else []
    ofs_elec = ofs_all_electronicas([str(f.get("of_devolucion", "")) for f in filas])
    por_num_doc = {str(f.get("num_doc")): f for f in filas}

    log = log_de(None)
    avisar(0, "")
    casos = []
    for i, num_doc in enumerate(docs, start=1):
        row = por_num_doc.get(num_doc, {"num_doc": num_doc})
        casos.append(_evaluar_un_caso(sesion, row, archivados, ofs_elec, log))
        avisar(i, num_doc)

    conformes = sum(1 for c in casos if c.get("nivel") == "ok")
    return resultado(True, f"{conformes} de {len(casos)} caso(s) conforme(s)", casos=casos)


def subsanar(acciones: list[dict], callback_progreso=None) -> dict:
    """Ejecuta las acciones correctivas elegidas sobre los casos observados."""
    log = log_de(callback_progreso)
    hechas = []
    for i, accion in enumerate(acciones or [], start=1):
        num_doc = str(accion.get("num_doc", ""))
        tipo = str(accion.get("accion", "crear_carpeta"))
        log(f"[{i}/{len(acciones or [])}] {tipo} en {num_doc}")
        if tipo == "crear_carpeta":
            fila = _fila_de(num_doc) or {"num_doc": num_doc}
            Path(resolver_carpeta_caso(fila)[1]).mkdir(parents=True, exist_ok=True)
        hechas.append(num_doc)
    return resultado(True, f"{len(hechas)} subsanación(es) aplicada(s)", oks=hechas)


def exportar_resumen(casos: list[dict], destino: str | None = None) -> str:
    """Escribe el resumen de validación como CSV y devuelve su ruta."""
    import csv
    import tempfile

    ruta = Path(destino or Path(tempfile.gettempdir()) / "resumen_validacion.csv")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", newline="", encoding="utf8") as fh:
        w = csv.writer(fh)
        w.writerow(["num_doc", "nivel", "carpeta_existe", "alertas"])
        for c in casos or []:
            w.writerow([
                c.get("num_doc", ""), c.get("nivel", ""),
                "SI" if c.get("carpeta_existe") else "NO",
                " | ".join(a.get("mensaje", "") for a in c.get("alertas", [])),
            ])
    return str(ruta)


def borrar_caso_completo(num_doc: str, borrar_carpeta: bool = False) -> dict:
    """Elimina el caso de la BD local y, opcionalmente, su carpeta."""
    import shutil

    from MACRO.database import borrar_caso

    fila = _fila_de(num_doc)
    if borrar_carpeta and fila:
        shutil.rmtree(resolver_carpeta_caso(fila)[1], ignore_errors=True)
    try:
        borrar_caso(str(num_doc))
    except Exception as exc:  # noqa: BLE001
        return resultado(False, f"No se pudo borrar: {exc}")
    return resultado(True, f"Caso {num_doc} eliminado")


__all__ = [
    "validar_casos", "subsanar", "exportar_resumen", "borrar_caso_completo",
    "resolver_carpeta_caso", "obtener_datos_incluye_archivo", "num_docs_archivados",
    "ofs_all_electronicas",
]
