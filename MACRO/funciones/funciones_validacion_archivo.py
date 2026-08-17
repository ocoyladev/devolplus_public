"""Reglas puras de 'Validar archivo': completitud de insumos y elementos
indispensables por tipo de expediente. Sin efectos de red ni de BD."""
from __future__ import annotations

import fnmatch
import os

# Elementos esperados dentro de ARCHIVOS_FINALES (insumo final del proceso PAPELES_TRABAJO).
INSUMO_FINAL: dict[str, list[str]] = {
    "ELECTRONICO": ["reportes_internos.pdf", "cedula_verificacion.pdf"],
    "FISICO": ["IMPR.pdf", "RI_IMPR.pdf"],
    # VIRTUAL se evalúa por patrón (consolidado / _FOLIADO), no por nombre fijo.
}

_SUBCARPETAS_PAPELES_TRABAJO = ("ARCHIVOS_INICIALES", "ARCHIVOS_FINALES", "PAPELES_TRABAJO")


def existe_patron(directorio: str, patron: str) -> bool:
    """True si alguna entrada de ``directorio`` (archivo o carpeta) casa el
    patrón glob (case-insensitive)."""
    if not directorio or not os.path.isdir(directorio):
        return False
    pl = patron.lower()
    for nombre in os.listdir(directorio):
        if fnmatch.fnmatch(nombre.lower(), pl):
            return True
    return False


def _detalle_carga(reportes: bool, cedula: bool) -> str:
    """Descripción de qué PDFs de carga se encontraron."""
    if reportes and cedula:
        return "ambos"
    if reportes:
        return "solo reportes_internos"
    if cedula:
        return "solo cedula_verificacion"
    return "ninguno"


# --- Visibilidad de los PDF cargados al expediente electrónico (1649) --------
# lstDocExp repite la misma información en varias claves; verificado contra un
# expediente real: 'Uso Interno' == indVis/indVisible 'NO' == indVisibleCod '0';
# 'Contribuyente' == 'SI' == '1'. Se consultan en orden y gana la primera que
# resuelve. Los PDF de la carga SIEMPRE deben quedar como NO visibles.
_CLAVES_VISIBILIDAD = ("indVisible", "indVis", "indVisibleCod")
_VALOR_VISIBLE = {"si", "sí", "s", "1", "true"}
_VALOR_NO_VISIBLE = {"no", "n", "0", "false"}
_ACCESO_VISIBLE = "contribuyente"
_ACCESO_NO_VISIBLE = "uso interno"

VISIBLE_SI = "si"
VISIBLE_NO = "no"
VISIBLE_DESCONOCIDO = "desconocido"


def visibilidad_documento(doc: dict | None) -> str:
    """¿El documento de ``lstDocExp`` es visible al contribuyente?

    Devuelve ``'si'``, ``'no'`` o ``'desconocido'``. Nunca asume ``'no'`` ante un
    campo ausente o un valor inesperado: si ACME cambiara el esquema, un
    documento visible debe salir a la luz como 'desconocido', no como correcto.
    """
    if not isinstance(doc, dict):
        return VISIBLE_DESCONOCIDO
    for clave in _CLAVES_VISIBILIDAD:
        if clave not in doc:
            continue
        valor = str(doc[clave]).strip().lower()
        if valor in _VALOR_VISIBLE:
            return VISIBLE_SI
        if valor in _VALOR_NO_VISIBLE:
            return VISIBLE_NO
    acceso = str(doc.get("desAcceso", "") or "").strip().lower()
    if acceso == _ACCESO_VISIBLE:
        return VISIBLE_SI
    if acceso == _ACCESO_NO_VISIBLE:
        return VISIBLE_NO
    return VISIBLE_DESCONOCIDO


def buscar_doc_carga(docs: list[dict] | None, cod_tipo_doc: str,
                     claves_texto: tuple[str, ...]) -> dict | None:
    """Documento de ``lstDocExp`` correspondiente a un PDF de la carga 1649.

    Prioriza ``codTipDoc`` (código exacto del tipo de documento, el mismo que usa
    la carga); si no viene, cae al match por texto sobre la descripción, que es
    la heurística previa. Devuelve el documento o None.
    """
    for d in docs or []:
        cod = str(d.get("codTipDoc", "") or d.get("codTipoDocumento", "") or "").strip()
        if cod and cod == cod_tipo_doc:
            return d
    for d in docs or []:
        texto = " ".join(str(d.get(k, "") or "") for k in
                         ("numDoc", "desArch", "descArchivo", "desTipdoc")).lower()
        if all(c in texto for c in claves_texto):
            return d
    return None


def _visibilidad_carga(carga: dict) -> list[tuple[str, str]]:
    """[(nombre_pdf, estado_visibilidad)] de los PDF que SÍ están en el
    expediente.

    Sin Portal, o si el PDF ni siquiera está cargado, no hay visibilidad que
    evaluar: esos casos ya los reportan las alertas de carga.
    """
    if carga.get("remoto") == "no_verificado":
        return []
    pares = (("reportes_internos.pdf", "remoto_reportes", "visible_reportes"),
             ("cedula_verificacion.pdf", "remoto_cedula", "visible_cedula"))
    return [(nombre, str(carga.get(clave_vis, VISIBLE_DESCONOCIDO)))
            for nombre, clave_remota, clave_vis in pares if carga.get(clave_remota)]


def repositorio_reales(repositorio_dir: str) -> list[str]:
    """Subcarpetas de REPOSITORIO con al menos un archivo (recursivo).

    Ignora placeholders vacíos que no referencian ningún expediente (fuente de
    falsas alertas)."""
    if not repositorio_dir or not os.path.isdir(repositorio_dir):
        return []
    reales = []
    for nombre in sorted(os.listdir(repositorio_dir)):
        sub = os.path.join(repositorio_dir, nombre)
        if not os.path.isdir(sub):
            continue
        if any(files for _root, _dirs, files in os.walk(sub)):
            reales.append(nombre)
    return reales


def evaluar_paso_papeles_trabajo(carpeta: str) -> bool:
    """True si existen las tres subcarpetas que crea 'Generar PAPELES_TRABAJO'."""
    if not carpeta or not os.path.isdir(carpeta):
        return False
    return all(os.path.isdir(os.path.join(carpeta, s)) for s in _SUBCARPETAS_PAPELES_TRABAJO)


def detectar_consolidado_foliado(af_dir: str) -> tuple[bool, bool]:
    """(hay_consolidado, hay_foliado) en ARCHIVOS_FINALES para expediente virtual.

    Consolidado = un *.pdf que NO termina en _FOLIADO.pdf. Foliado = *_FOLIADO.pdf.
    """
    if not af_dir or not os.path.isdir(af_dir):
        return (False, False)
    consolidado = foliado = False
    for nombre in os.listdir(af_dir):
        low = nombre.lower()
        if not low.endswith(".pdf"):
            continue
        if low.endswith("_foliado.pdf"):
            foliado = True
        else:
            consolidado = True
    return (consolidado, foliado)


def evaluar_insumo_final(af_dir: str, tipo: str) -> dict:
    """Completitud de ARCHIVOS_FINALES según el tipo de expediente."""
    if tipo == "VIRTUAL":
        consolidado, foliado = detectar_consolidado_foliado(af_dir)
        faltantes: list[str] = []
        if not consolidado:
            faltantes.append("consolidado")
        if not foliado:
            faltantes.append("consolidado foliado")
        return {
            "completo": not faltantes,
            "faltantes": faltantes,
            "puede_foliar": (not foliado) and consolidado,
        }

    esperados = INSUMO_FINAL.get(tipo, [])
    faltantes = [f for f in esperados if not existe_patron(af_dir, f)]
    return {"completo": not faltantes, "faltantes": faltantes, "puede_foliar": False}


# Patrones indispensables (glob, case-insensitive). "(I)" en el spec.
_IND_ELECTRONICO = ["*_planeamiento.pdf", "MACRO.xlsx", "Reporte de Tareas*.pdf", "REF.pdf"]
_IND_FISICO = _IND_ELECTRONICO + ["RI_*_NOT.pdf", "RI_*.pdf", "Consulta Detalle*", "*_of.pdf"]
_IND_VIRTUAL = _IND_FISICO + ["REPOSITORIO"]
_IND_MULTIPLE_RAIZ = ["*_planeamiento.pdf", "Reporte de Tareas*.pdf", "REF.pdf", "Consulta Detalle*"]
_IND_MULTIPLE_SUB = ["MACRO.xlsx", "RI_*_NOT.pdf", "RI_*.pdf"]

_IND_SINGLE = {
    "ELECTRONICO": _IND_ELECTRONICO,
    "FISICO": _IND_FISICO,
    "VIRTUAL": _IND_VIRTUAL,
}


def patrones_indispensables(tipo: str, is_multiple: bool) -> dict:
    """Patrones indispensables a verificar. En OF_MULTIPLE se reparten entre la
    raíz (ARCHIVOS_INICIALES) y cada subcarpeta de caso (num_doc)."""
    if is_multiple:
        return {"raiz": list(_IND_MULTIPLE_RAIZ), "sub": list(_IND_MULTIPLE_SUB)}
    return {"raiz": list(_IND_SINGLE.get(tipo, _IND_ELECTRONICO)), "sub": []}


def evaluar_indispensables(directorio: str, patrones: list[str]) -> list[dict]:
    """Por cada patrón, marca si hay al menos una entrada que lo cumpla."""
    return [{"patron": p, "encontrado": existe_patron(directorio, p)} for p in patrones]


def _faltantes_indispensables(indispensables: dict) -> list[str]:
    faltan = [r["patron"] for r in indispensables.get("raiz", []) if not r["encontrado"]]
    for _doc, items in indispensables.get("subcarpetas", {}).items():
        faltan += [r["patron"] for r in items if not r["encontrado"]]
    return faltan


def construir_alertas(caso: dict) -> None:
    """Rellena caso['alertas'] y caso['nivel'] a partir de los checks ya hechos."""
    alertas: list[dict] = []

    if not caso["carpeta_existe"]:
        alertas.append({"codigo": "sin_carpeta", "severidad": "error",
                        "mensaje": "No se encontró la carpeta del caso.", "accion": ""})
        caso["alertas"] = alertas
        caso["nivel"] = "error"
        return

    # Una rectificatoria (tipo 12) no arma PAPELES_TRABAJO propio: hereda ARCHIVOS_FINALES
    # de su solicitud de origen. No se le exigen subcarpetas ni indispensables.
    es_t12 = bool(caso.get("es_tipo12"))

    if es_t12:
        if not caso.get("origen_tipo12"):
            alertas.append({"codigo": "tipo12_sin_origen", "severidad": "error",
                            "mensaje": "Rectificatoria tipo 12: no se pudo resolver "
                                       "su solicitud de origen (num_doc_aso).",
                            "accion": ""})
        insumo = caso["insumo_final"]
        if not insumo["completo"]:
            faltan = ", ".join(insumo["faltantes"]) or "elementos"
            # 'papeles_trabajo' a secas correría solo sobre la rectificatoria y caería en el
            # camino SINGLE, que la rechaza por no tener origen: hay que rehacer
            # la OF entera para que el origen se arme y le herede su armado.
            alertas.append({"codigo": "insumo_incompleto", "severidad": "error",
                            "mensaje": f"ARCHIVOS_FINALES incompleto: falta {faltan}. "
                                       "Se hereda del origen al regenerar el PAPELES_TRABAJO "
                                       "de la OF completa.",
                            "accion": "papeles_trabajo_of"})
    elif not caso["paso_papeles_trabajo"]:
        alertas.append({"codigo": "sin_papeles_trabajo", "severidad": "error",
                        "mensaje": "No pasó por 'Generar PAPELES_TRABAJO' (faltan subcarpetas).",
                        "accion": "papeles_trabajo"})
    else:
        insumo = caso["insumo_final"]
        if not insumo["completo"]:
            accion = "foliar" if insumo["puede_foliar"] else "papeles_trabajo_revertir"
            faltan = ", ".join(insumo["faltantes"]) or "elementos"
            alertas.append({"codigo": "insumo_incompleto", "severidad": "error",
                            "mensaje": f"ARCHIVOS_FINALES incompleto: falta {faltan}.",
                            "accion": accion})

    exp = caso["exp_repositorio"]
    repositorios = caso.get("repositorios", [])
    if caso["tipo_exp"] in ("ELECTRONICO", "VIRTUAL") and repositorios \
            and not exp["registrado"] and not exp["autoregistrado"]:
        # En una tipo 12 la columna la puebla 'Generar PAPELES_TRABAJO' desde el origen: no
        # hay REPOSITORIO local que registrar, así que no se ofrece esa acción.
        alertas.append({"codigo": "exp_repositorio_faltante", "severidad": "advertencia",
                        "mensaje": "Hay REPOSITORIO pero la columna Exp. REPOSITORIO está vacía.",
                        "accion": "" if es_t12 else "registrar_repositorio"})
    if caso["tipo_exp"] in ("ELECTRONICO", "VIRTUAL"):
        for it in repositorios:
            if it["estado"] == "pendiente_subir":
                # 'subir_repositorio' (vía especial), NO 'cargar_expediente': esta
                # última carga reportes_internos/cedula al 1649, que es otra cosa.
                # El denom viaja aparte porque la acción lo necesita como insumo.
                alertas.append({"codigo": "repositorio_item", "severidad": "advertencia",
                                "mensaje": f"Repositorio '{it['denom']}' no figura en el "
                                           "expediente electrónico.",
                                "accion": "subir_repositorio", "item": it["denom"]})
            elif it["estado"] == "manual":
                # 'pdf_ok' (el <denom>.pdf compilado ya está en ARCHIVOS_INICIALES)
                # no cae aquí a propósito: ese repositorio ya se incorporó y no
                # necesita intervención.
                alertas.append({"codigo": "repositorio_item", "severidad": "advertencia",
                                "mensaje": f"Repositorio '{it['denom']}' requiere evaluación "
                                           "manual: no se sube automáticamente y no se "
                                           "encontró su PDF en ARCHIVOS_INICIALES.",
                                "accion": ""})
            elif it["estado"] == "no_verificado":
                alertas.append({"codigo": "repositorio_item", "severidad": "advertencia",
                                "mensaje": f"Repositorio '{it['denom']}': no se pudo verificar "
                                           "(sin Portal).",
                                "accion": ""})

    carga = caso["carga_1649"]
    if carga.get("aplica"):
        local = _detalle_carga(carga["local"]["reportes"], carga["local"]["cedula"])
        if carga["remoto"] == "no_verificado":
            alertas.append({"codigo": "carga_no_verificada", "severidad": "advertencia",
                            "mensaje": f"Carga al expediente no verificada (sin Portal). "
                                       f"Local: {local}.",
                            "accion": ""})
        elif carga["remoto"] == "faltante":
            remoto = _detalle_carga(carga["remoto_reportes"], carga["remoto_cedula"])
            alertas.append({"codigo": "carga_remota_faltante", "severidad": "advertencia",
                            "mensaje": f"Expediente electrónico — encontrado: {remoto}. "
                                       f"Local: {local}.",
                            "accion": "cargar_expediente"})

        visibles = [n for n, estado in _visibilidad_carga(carga)
                    if estado == VISIBLE_SI]
        if visibles:
            alertas.append({"codigo": "carga_visible_contribuyente", "severidad": "error",
                            "mensaje": f"VISIBLE AL CONTRIBUYENTE en el expediente: "
                                       f"{', '.join(visibles)}. Debe figurar como "
                                       f"'Uso Interno'; corregirlo en el expediente.",
                            "accion": ""})
        indeterminados = [n for n, estado in _visibilidad_carga(carga)
                          if estado == VISIBLE_DESCONOCIDO]
        if indeterminados:
            alertas.append({"codigo": "carga_visibilidad_desconocida",
                            "severidad": "advertencia",
                            "mensaje": "No se pudo determinar la visibilidad de: "
                                       f"{', '.join(indeterminados)}. Verificar "
                                       "manualmente en el expediente.",
                            "accion": ""})

    faltan_ind = _faltantes_indispensables(caso["indispensables"])
    if faltan_ind:
        sev = "error" if caso["paso_papeles_trabajo"] else "advertencia"
        alertas.append({"codigo": "indispensable_faltante", "severidad": sev,
                        "mensaje": "Faltan indispensables: " + ", ".join(faltan_ind) + ".",
                        "accion": "abrir_carpeta"})

    caso["alertas"] = alertas
    if any(a["severidad"] == "error" for a in alertas):
        caso["nivel"] = "error"
    elif alertas:
        caso["nivel"] = "advertencia"
    else:
        caso["nivel"] = "ok"
