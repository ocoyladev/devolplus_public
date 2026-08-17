import re
import pdfplumber
from datetime import datetime

# --- Funciones para procesamiento de Planeamiento (PDF) ---

UBIGEO_RE = re.compile(
    r"UBIGEO\s*:\s*(\d{6})\s*-\s*([A-ZÁÉÍÓÚÑ ]+?)\s*-\s*([A-ZÁÉÍÓÚÑ ]+?)\s*-\s*([A-ZÁÉÍÓÚÑ ]+)\b"
)

# Prefijos válidos (2 dígitos) para el N° de OF de devolución. Corresponden al
# año del documento (22=2022, 23=2023, ... 26=2026). Un N° que empiece con "0"
# (p. ej. "024...") es un RI y debe descartarse. Añadir nuevos prefijos aquí
# conforme avancen los años (p. ej. "27").
OF_PREFIJOS_VALIDOS = ("22", "23", "24", "25", "26")


def _es_of_valida(val: str) -> bool:
    """True si el número corresponde a una OF de devolución (no a un RI)."""
    return bool(val) and val[:2] in OF_PREFIJOS_VALIDOS


ROW_RE = re.compile(
    r"^0023\s+024\s+"
    r"(?P<cod_for>\d{4})\s+"
    r"(?P<num_doc>\d+)\s+"
    r"(?P<per_doc>\d{6})\s+"
    r"(?P<cod_tri>\d{6})\s+"
    r"\d+\s+"                                 # ENTE (ej. 264)
    r"(?P<fec_doc>\d{2}/\d{2}/\d{4})\s+"
    r"(?P<cod_tip_sol>\d{2})\s+"
    r"(?P<mto_solicitado>[\d.,]+)\s+"
    r"(?P<mto_reconocido>[\d.,]+)\s+"          # MTO RECONOC (2º importe de la fila)
    r"(?P<cod_for_aso>\d{4}|-)"
    r"(?P<tail>.*)$",
    re.UNICODE
)

def leer_pdf_texto(ruta: str) -> list[str]:
    """Devuelve lista de líneas de texto del PDF."""
    texto = ""
    with pdfplumber.open(ruta) as pdf:
        for p in pdf.pages:
            texto += (p.extract_text() or "") + "\n"
    # Normalizaciones
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{2,}", "\n", texto)
    return texto.splitlines()

def extraer_info_general(lineas: list[str]) -> dict:
    info = {
        "num_ruc": "NO_ENCONTRADO",
        "ddp_nombre": "NO_ENCONTRADO",
        "direccion": "NO_ENCONTRADO",
        "departamento": "",
        "provincia": "",
        "distrito": "",
    }

    # RUC
    for ln in lineas:
        m = re.search(r"RUC[: ]+(\d{11})", ln)
        if m:
            info["num_ruc"] = m.group(1)
            break

    # Razón Social
    for ln in lineas:
        m = re.search(r"RAZÓN SOCIAL\s*:\s*([A-ZÁÉÍÓÚÑ ]+)", ln)
        if m:
            info["ddp_nombre"] = m.group(1).strip()
            break

    # Dirección
    for ln in lineas:
        m = re.search(r"DIRECCIÓN\s*:\s*(.+)", ln)
        if m:
            info["direccion"] = m.group(1).strip()
            break

    # UBIGEO -> solo para dep/prov/dist
    full_text = "\n".join(lineas)
    m = UBIGEO_RE.search(full_text)
    if m:
        info["departamento"] = m.group(2).strip()
        info["provincia"] = m.group(3).strip()
        distrito = m.group(4).strip()
        # limpiar caso "SISTEMA DE CONTABILIDAD"
        if distrito.endswith("SISTEMA DE CONTABILIDAD"):
            distrito = distrito.replace("SISTEMA DE CONTABILIDAD", "").strip()
        info["distrito"] = distrito

    return info

def reconstruir_num_doc_aso(lineas: list[str], idx_row: int) -> str:
    """
    Construye el num_doc_aso:
    - hasta 10 dígitos iniciales de la línea anterior (si existen).
    - +1 dígito inicial de la línea siguiente si comienza con número y la línea < 15 caracteres.
    """
    prev_val = ""
    next_val = ""

    if idx_row > 0:
        prev_line = lineas[idx_row - 1].strip()
        m = re.match(r"(\d{1,10})", prev_line)  # primeros hasta 10 dígitos iniciales
        if m:
            prev_val = m.group(1)

    if idx_row + 1 < len(lineas):
        next_line = lineas[idx_row + 1].strip()
        if len(next_line) < 15:
            m = re.match(r"(\d)", next_line)  # solo primer dígito inicial
            if m:
                next_val = m.group(1)

    return (prev_val + next_val).strip()

def extraer_of_devolucion(tail: str, lineas: list[str], idx_row: int) -> str:
    """
    Captura N° OF (prefijos válidos en OF_PREFIJOS_VALIDOS: 22..26). Si es
    '024...' (u otro prefijo no válido) es un RI y se descarta.
    """
    # mismo renglón
    m = re.search(r"\bNO\s+(\d+)", tail)
    if m:
        val = m.group(1)
        return val if _es_of_valida(val) else ""

    # revisar líneas siguientes
    for j in (idx_row + 1, idx_row + 2):
        if 0 <= j < len(lineas):
            mm = re.search(r"\bNO\s+(\d+)", lineas[j])
            if mm:
                val = mm.group(1)
                return val if _es_of_valida(val) else ""
    return ""

# Resultados posibles de una solicitud en el planeamiento y su forma redactada.
# 'Autorización de emisión' se redacta como 'Autorizada'.
RESULTADOS_PLANEAMIENTO = {
    "AUTORIZACIÓN DE EMISIÓN": "Autorizada",
    "AUTORIZACION DE EMISION": "Autorizada",
    "IMPROCEDENTE": "Improcedente",
    "DENEGADA": "Denegado",
    "DENEGADO": "Denegado",
    "PENDIENTE": "Pendiente",
}


def _extraer_resultado_tail(tail: str) -> str:
    """Devuelve el resultado redactado hallado en el tail, o '' si no hay."""
    t = (tail or "").upper()
    # 'Autorización de emisión' primero (contiene 'EMISIÓN', evita falsos positivos).
    for clave, redactado in RESULTADOS_PLANEAMIENTO.items():
        if clave in t:
            return redactado
    return ""


def _extraer_ri_tail(tail: str, of_dev: str) -> str:
    """Extrae el N° de RI del tail. Suele iniciar en '024'; se evita el N° de OF."""
    tokens = re.findall(r"\d{6,}", tail or "")
    # Preferir un token que empiece por '024' (patrón habitual del RI).
    for tok in tokens:
        if tok.startswith("024") and tok != of_dev:
            return tok
    # Fallback: primer numérico largo que no sea la OF.
    for tok in tokens:
        if tok != of_dev:
            return tok
    return ""


def extraer_solicitudes(lineas: list[str], detallado: bool = False) -> list[dict]:
    """Extrae las solicitudes del planeamiento.

    Con ``detallado=True`` agrega los campos de antecedentes (mto_reconocido,
    num_ri, resultado) usados por el REF.docx. Por defecto NO se agregan, para no
    contaminar la carga SISTEMA_LEGACY (que usa estas filas como datos del caso).
    """
    solicitudes = []
    for i, ln in enumerate(lineas):
        m = ROW_RE.match(ln)
        if not m:
            continue

        cod_for       = m.group("cod_for")
        num_doc       = m.group("num_doc")
        per_doc       = m.group("per_doc")
        cod_tri       = m.group("cod_tri")
        fec_doc_str   = m.group("fec_doc")
        cod_tip_sol   = m.group("cod_tip_sol")
        mto_solic_raw = m.group("mto_solicitado")
        mto_recon_raw = m.group("mto_reconocido")
        cod_for_aso   = m.group("cod_for_aso")
        tail          = m.group("tail") or ""

        # OF
        of_dev = extraer_of_devolucion(tail, lineas, i)
        if not of_dev and not detallado:
            # Modo carga (SISTEMA_LEGACY): descartamos filas sin OF válido (p. ej. las ya
            # resueltas cuyo N° tras 'NO' es un RI 024...). En modo detallado
            # (antecedentes) se conservan, pues son justamente los antecedentes.
            continue

        # N° Asocia
        num_doc_aso = reconstruir_num_doc_aso(lineas, i)

        # normalizaciones
        def _a_float(raw):
            v = str(raw).replace(".", "").replace(",", ".")
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        mto = _a_float(mto_solic_raw)
        mto_recon = _a_float(mto_recon_raw)

        try:
            fec_doc = datetime.strptime(fec_doc_str, "%d/%m/%Y").date()
        except:
            fec_doc = fec_doc_str

        fila = {
            "of_devolucion": of_dev,
            "cod_for": cod_for,
            "num_doc": num_doc,
            "per_doc": per_doc,
            "cod_tri": cod_tri,
            "fec_doc": fec_doc,
            "cod_tip_sol": cod_tip_sol,
            "mto_solicitado": mto,
            "cod_for_aso": cod_for_aso,
            "num_doc_aso": num_doc_aso,
        }
        if detallado:
            fila["mto_reconocido"] = mto_recon
            fila["num_ri"] = _extraer_ri_tail(tail, of_dev)
            fila["resultado"] = _extraer_resultado_tail(tail)
        solicitudes.append(fila)
    return solicitudes

def procesar_pdf(ruta: str, detallado: bool = False) -> list[dict]:
    lineas = leer_pdf_texto(ruta)
    info = extraer_info_general(lineas)
    solicitudes = extraer_solicitudes(lineas, detallado=detallado)

    registros = []
    for sol in solicitudes:
        registros.append({**info, **sol})
    return registros


# Tributo por defecto a evaluar en el planeamiento: Renta de Persona Natural.
TRIBUTO_RENTA_PN = "030703"
