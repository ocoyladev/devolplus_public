import os
import sys
import math
import re
from datetime import date, datetime
import pandas as pd
from decimal import Decimal, InvalidOperation
from tkinter import Tk, filedialog


# ---------------------------------------------------------------------------
# Utilidades centrales de fechas
# ---------------------------------------------------------------------------
# Toda la app debe persistir fechas en SQLite local como string "DD/MM/YYYY".
# Estas helpers son la única fuente de verdad para parsear y formatear.

_TOKENS_VACIOS_FECHA = {"", "nan", "nat", "none", "null"}
_RE_FECHA_ISO = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}(?:[ T]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?$")
_RE_FECHA_SLASH = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")


def parsear_fecha(valor):
    """Parsea un valor heterogéneo a `pd.Timestamp` o `pd.NaT`.

    Reglas:
    - `datetime`/`date`/`pd.Timestamp` se devuelven (normalizados a Timestamp).
    - Strings ISO `YYYY-MM-DD[ HH:MM:SS]` se parsean como ISO.
    - Strings `DD/MM/YYYY` (con `/`) se parsean siempre como dayfirst.
    - Vacíos, "nan", "NaT", None → NaT.
    """
    if valor is None:
        return pd.NaT

    # Si es Timestamp o datetime, normalizar
    if isinstance(valor, pd.Timestamp):
        return pd.NaT if pd.isna(valor) else valor
    if isinstance(valor, datetime):
        return pd.Timestamp(valor)
    if isinstance(valor, date):
        return pd.Timestamp(valor)

    # Float NaN
    if isinstance(valor, float) and (math.isnan(valor) or math.isinf(valor)):
        return pd.NaT

    texto = str(valor).strip()
    if texto.lower() in _TOKENS_VACIOS_FECHA:
        return pd.NaT

    # Excel a veces serializa fechas como número serial; lo dejamos pasar a pandas
    if _RE_FECHA_ISO.match(texto):
        return pd.to_datetime(texto, errors="coerce")
    if _RE_FECHA_SLASH.match(texto):
        return pd.to_datetime(texto, dayfirst=True, errors="coerce")

    # Último recurso: dejar que pandas lo intente con dayfirst (favorece formato local)
    return pd.to_datetime(texto, dayfirst=True, errors="coerce")


def formatear_ddmmyyyy(valor):
    """Devuelve siempre `str` "DD/MM/YYYY" o `""` si el valor no es interpretable."""
    ts = parsear_fecha(valor)
    if ts is None or pd.isna(ts):
        return ""
    return ts.strftime("%d/%m/%Y")


# ---------------------------------------------------------------------------
# Ventana horaria de descargas de planeamiento
# ---------------------------------------------------------------------------
# Para no saturar el servidor, las descargas de planeamiento no se ejecutan en
# horario laboral: lunes a viernes de 08:00 a 17:00 (hora de Lima, Perú). Los
# fines de semana están siempre permitidas.
PLANEAMIENTO_HORA_INICIO = 8   # 08:00 (inclusive) inicia el bloqueo
PLANEAMIENTO_HORA_FIN = 17     # 17:00 (exclusive) termina el bloqueo


def _ahora_lima():
    """Devuelve la hora actual en Lima (America/Lima); cae a la hora local del equipo."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("America/Lima"))
    except Exception:
        return datetime.now()


def planeamiento_permitido(ahora=None):  # noqa: ARG001 - firma conservada por compatibilidad
    """Las descargas de planeamiento ya no tienen restricción horaria.

    Antes se bloqueaban de lunes a viernes entre las 08:00 y las 17:00 (hora de
    Lima). Esa limitación se retiró: ahora siempre están permitidas. Se conserva la
    función (y su parámetro ``ahora``) para no romper los llamadores existentes.
    """
    return True


# Columnas que el código trata como fechas en tabla_asign y tabla_bd
COLUMNAS_FECHA_DB = (
    "fec_solicitud",
    "fec_doc",
    "fec_doc_aso",
    "f_presenta",
    "f_presenta_ult",
    "VctoInd",
    "CalcVctoInd",
    "fecha_carta",
    "fecha_ri",
    "fec_ri",
    "fec_act",
)


def normalizar_columnas_fecha(df, columnas=None):
    """Convierte in-place las columnas-fecha del DataFrame a strings DD/MM/YYYY.

    Cualquier valor que no sea fecha válida se sustituye por `None` (se guarda como NULL).
    """
    if df is None or df.empty:
        return df
    columnas = columnas or COLUMNAS_FECHA_DB
    for col in columnas:
        if col in df.columns:
            df[col] = df[col].map(lambda v: formatear_ddmmyyyy(v) or None)
    return df


def parsear_columnas_fecha(df, columnas=None):
    """Convierte in-place las columnas-fecha de un DataFrame a `pd.Timestamp`."""
    if df is None or df.empty:
        return df
    columnas = columnas or COLUMNAS_FECHA_DB
    for col in columnas:
        if col in df.columns:
            df[col] = df[col].map(parsear_fecha)
    return df


def asignar_fecha_celda(ws, celda, valor, formato_excel="DD/MM/YYYY"):
    """Escribe `valor` en `ws[celda]` como objeto datetime con `number_format` dado.

    Si no es interpretable, escribe string vacío.
    """
    ts = parsear_fecha(valor)
    if ts is None or pd.isna(ts):
        ws[celda] = ""
        return
    ws[celda] = ts.to_pydatetime()
    ws[celda].number_format = formato_excel


import ctypes
from ctypes import wintypes

def set_cell_numeric_if_possible(ws, cell_ref, value):
    """
    Intenta convertir el valor a número (float) y lo asigna.
    Si no es convertible, escribe tal cual (o vacío si None/NaN).
    No cambia number_format: respeta el de la plantilla.
    """
    num = _coerce_to_number(value)
    if num is None:
        if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
            ws[cell_ref] = ""
        else:
            ws[cell_ref] = value
    else:
        ws[cell_ref] = num

def leer_credenciales(filepath):
    """Lee el usuario y la contraseña desde un archivo."""
    if not filepath: return None, None
    try:
        with open(filepath, 'r') as f:
            lineas = f.read().splitlines()
            if len(lineas) >= 2:
                return lineas[0].strip(), lineas[1].strip()
            else:
                print("Error: El archivo de credenciales debe tener al menos dos líneas.")
                return None, None
    except Exception as e:
        print(f"Error al leer el archivo de credenciales: {e}")
        return None, None

def leer_num_docs_de_txt(filepath):
    """Lee los números de documento del archivo de entrada."""
    if not filepath: return None
    try:
        with open(filepath, 'r') as f:
            num_docs = [line.strip() for line in f if line.strip()]
        return num_docs if num_docs else None
    except Exception as e:
        print(f"Error al leer el archivo de documentos: {e}")
        return None

def obtener_base_path():
    """Devuelve la ruta base del ejecutable o del script actual."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

import ctypes
from ctypes import wintypes

# def seleccionar_archivo(titulo, tipo_archivo="texto"):
#     """
#     Abre un diálogo nativo de Windows para seleccionar archivo (sin usar Tkinter).
#     Returns path or empty string if cancelled.
#     """
#     if tipo_archivo == "texto":
#         filter_str = "Archivos de texto\0*.txt\0Todos los archivos\0*.*\0\0"
#     elif tipo_archivo == "excel":
#         filter_str = "Archivos de Excel\0*.xlsx;*.xls\0Todos los archivos\0*.*\0\0"
#     elif tipo_archivo == "excel93":
#         filter_str = "Archivos de Excel 97-2003\0*.xls\0Todos los archivos\0*.*\0\0"
#     else:
#         filter_str = "Todos los archivos\0*.*\0\0"
        
#     # Estructura OPENFILENAME para GetOpenFileName
#     # Usamos una implementación simplificada invocando directamente a la API si es posible,
#     # pero para robustez en python puro sin dependencias extras como pywin32,
#     # ctypes es verboso.
    
#     # Alternativa rápida: Usar Tkinter en el hilo principal ES REQUERIDO si usamos Tk.
#     # Si Flet ocupa el hilo principal, Tkinter falla.
#     # Solución: Usar PowerShell para abrir el diálogo (truco sucio pero efectivo sin depedencias).
    
#     ps_script = f"""
#     Add-Type -AssemblyName System.Windows.Forms
#     $f = New-Object System.Windows.Forms.OpenFileDialog
#     $f.Title = "{titulo}"
#     $f.Filter = "{filter_str.replace(chr(0), '|')}"
#     if ($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
#         $f.FileName
#     }}
#     """
#     # Limpiar filter string para powershell (Format: "Text files (*.txt)|*.txt|All files (*.*)|*.*")
#     if tipo_archivo == "texto":
#         ps_filter = "Archivos de texto (*.txt)|*.txt|Todos los archivos (*.*)|*.*"
#     elif "excel" in tipo_archivo:
#         ps_filter = "Archivos de Excel (*.xlsx;*.xls)|*.xlsx;*.xls|Todos los archivos (*.*)|*.*"
#     else:
#         ps_filter = "Todos los archivos (*.*)|*.*"
        
#     # cmd = [
#     #     "powershell", 
#     #     "-NoProfile", 
#     #     "-Command", 
#     #     f"""
#     #     Add-Type -AssemblyName System.Windows.Forms
#     #     $f = New-Object System.Windows.Forms.OpenFileDialog
#     #     $f.Title = '{titulo}'
#     #     $f.Filter = '{ps_filter}'
#     #     $f.TopMost = $true
#     #     if ($f.ShowDialog() -eq 'OK') {{ Write-Host $f.FileName }}
#     #     """
#     # ]
#         # En MACRO/funciones/funciones_generales.py
#     cmd = [
#         "powershell", 
#         "-NoProfile", 
#         "-Command", 
#         f"""
#         Add-Type -AssemblyName System.Windows.Forms
#         $form = New-Object System.Windows.Forms.Form
#         $form.TopMost = $true
        
#         $f = New-Object System.Windows.Forms.OpenFileDialog
#         $f.Title = '{titulo}'
#         $f.Filter = '{ps_filter}'
        
#         # Le pasamos $form como dueño para forzar el primer plano
#         if ($f.ShowDialog($form) -eq 'OK') {{ Write-Host $f.FileName }}
#         $form.Dispose()
#         """
#     ]
    
#     try:
#         import subprocess
#         # Create startupinfo to hide console window
#         startupinfo = subprocess.STARTUPINFO()
#         startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
#         result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
#         return result.stdout.strip()
#     except Exception as e:
#         print(f"Error abriendo diálogo: {e}")
#         return ""

# def seleccionar_carpeta(titulo):
#     """Abre diálogo de selección de carpeta usando PowerShell (sin Tkinter)."""
#     # cmd = [
#     #     "powershell", 
#     #     "-NoProfile", 
#     #     "-Command", 
#     #     f"""
#     #     Add-Type -AssemblyName System.Windows.Forms
#     #     $f = New-Object System.Windows.Forms.FolderBrowserDialog
#     #     $f.Description = '{titulo}'
#     #     $f.RootFolder = 'MyComputer'
#     #     if ($f.ShowDialog() -eq 'OK') {{ Write-Host $f.SelectedPath }}
#     #     """
#     # ]

#         # En MACRO/funciones/funciones_generales.py
#     cmd = [
#         "powershell", 
#         "-NoProfile", 
#         "-Command", 
#         f"""
#         Add-Type -AssemblyName System.Windows.Forms
#         $form = New-Object System.Windows.Forms.Form
#         $form.TopMost = $true
        
#         $f = New-Object System.Windows.Forms.FolderBrowserDialog
#         $f.Description = '{titulo}'
#         $f.RootFolder = 'MyComputer'
        
#         # Le pasamos $form como dueño para forzar el primer plano
#         if ($f.ShowDialog($form) -eq 'OK') {{ Write-Host $f.SelectedPath }}
#         $form.Dispose()
#         """
#     ]
#     try:
#         import subprocess
#         startupinfo = subprocess.STARTUPINFO()
#         startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
#         result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
#         return result.stdout.strip()
#     except Exception as e:
#         print(f"Error abriendo diálogo carpeta: {e}")
#         return ""

def seleccionar_archivo(titulo, tipo_archivo="texto"):
    """
    Abre un diálogo nativo de Windows (OpenFileDialog) usando la API Win32.
    Se bloquea modalmente a la ventana principal de la aplicación.
    """
    if tipo_archivo == "texto":
        filter_str = "Archivos de texto\0*.txt\0Todos los archivos\0*.*\0\0"
    elif "excel" in tipo_archivo:
        filter_str = "Archivos de Excel\0*.xlsx;*.xls\0Todos los archivos\0*.*\0\0"
    else:
        filter_str = "Todos los archivos\0*.*\0\0"
        
    class OPENFILENAME(ctypes.Structure):
        _fields_ = [
            ("lStructSize", wintypes.DWORD),
            ("hwndOwner", wintypes.HWND),
            ("hInstance", wintypes.HINSTANCE),
            ("lpstrFilter", wintypes.LPCWSTR),
            ("lpstrCustomFilter", wintypes.LPWSTR),
            ("nMaxCustFilter", wintypes.DWORD),
            ("nFilterIndex", wintypes.DWORD),
            ("lpstrFile", wintypes.LPWSTR),
            ("nMaxFile", wintypes.DWORD),
            ("lpstrFileTitle", wintypes.LPWSTR),
            ("nMaxFileTitle", wintypes.DWORD),
            ("lpstrInitialDir", wintypes.LPCWSTR),
            ("lpstrTitle", wintypes.LPCWSTR),
            ("Flags", wintypes.DWORD),
            ("nFileOffset", wintypes.WORD),
            ("nFileExtension", wintypes.WORD),
            ("lpstrDefExt", wintypes.LPCWSTR),
            ("lCustData", wintypes.LPARAM),
            ("lpfnHook", ctypes.c_void_p),
            ("lpTemplateName", wintypes.LPCWSTR),
            ("pvReserved", ctypes.c_void_p),
            ("dwReserved", wintypes.DWORD),
            ("FlagsEx", wintypes.DWORD)
        ]
    
    ofn = OPENFILENAME()
    ofn.lStructSize = ctypes.sizeof(OPENFILENAME)
    
    # IMPORTANTE: Tomamos el Handel (HWND) de la propia ventana de la app
    # Esto une el diálogo a tu programa y por ley del OS debe estar al frente 
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    ofn.hwndOwner = hwnd
    ofn.lpstrFilter = filter_str
    
    # Creamos el buffer para capturar el texto
    buffer = ctypes.create_unicode_buffer(512)
    ofn.lpstrFile = ctypes.cast(buffer, wintypes.LPWSTR)
    ofn.nMaxFile = 512
    ofn.lpstrTitle = titulo
    
    # Banderas: OFN_EXPLORER (0x00080000), OFN_FILEMUSTEXIST (0x00001000) y OFN_NOCHANGEDIR (0x00000008)
    ofn.Flags = 0x00080000 | 0x00001000 | 0x00000008
    
    if ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
        return buffer.value
    return ""

def seleccionar_carpeta(titulo):
    """
    Abre diálogo de selección de carpeta nativo bloqueado al proceso en Flet.
    """
    class BROWSEINFO(ctypes.Structure):
        _fields_ = [
            ("hwndOwner", wintypes.HWND),
            ("pidlRoot", ctypes.c_void_p),
            ("pszDisplayName", wintypes.LPWSTR),
            ("lpszTitle", wintypes.LPCWSTR),
            ("ulFlags", wintypes.UINT),
            ("lpfn", ctypes.c_void_p),
            ("lParam", wintypes.LPARAM),
            ("iImage", ctypes.c_int)
        ]
    
    bi = BROWSEINFO()
    # Enlazar ventana superior local
    bi.hwndOwner = ctypes.windll.user32.GetForegroundWindow()
    bi.lpszTitle = titulo
    # BIF_RETURNONLYFSDIRS (0x01) | BIF_NEWDIALOGSTYLE (0x40 para moderno redimensionable)
    bi.ulFlags = 0x00000001 | 0x00000040
    
    # Inicializar COM para evitar errores con interfaces nuevas
    ctypes.windll.ole32.CoInitialize(None)
    
    pidl = ctypes.windll.shell32.SHBrowseForFolderW(ctypes.byref(bi))
    path = ""
    if pidl:
        buffer = ctypes.create_unicode_buffer(512)
        if ctypes.windll.shell32.SHGetPathFromIDListW(pidl, buffer):
            path = buffer.value
        # Liberar la memoria reservada para el puntero PIDL
        ctypes.windll.ole32.CoTaskMemFree(pidl)
        
    ctypes.windll.ole32.CoUninitialize()
    return path

def resource_path(relative_path):
    """ Obtiene la ruta absoluta al recurso, funciona para desarrollo y para PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Clave de ofuscación del .env embebido (.envx). NO es cifrado fuerte: solo evita
# que las credenciales aparezcan en texto plano dentro del .exe (p. ej. con
# `strings` o al desempaquetar). La barrera real de seguridad es usar un usuario
# Oracle de mínimos privilegios (solo las tablas de acceso), no el ADMIN.
_ENV_XOR_KEY = b"DEVOLPLUS_2026_ENVKEY_x99"


def _xor_bytes(data: bytes) -> bytes:
    k = _ENV_XOR_KEY
    return bytes(b ^ k[i % len(k)] for i, b in enumerate(data))


def ofuscar_env(texto: str) -> bytes:
    """Codifica el contenido de un .env para embeberlo sin texto plano.

    La usa la spec de PyInstaller al construir; ``cargar_env`` hace la inversa.
    """
    import base64
    return base64.b64encode(_xor_bytes(texto.encode("utf-8")))


def _desofuscar_env(blob: bytes) -> str:
    import base64
    return _xor_bytes(base64.b64decode(blob)).decode("utf-8")


def cargar_env():
    """Carga las credenciales (``.env``) para desarrollo y para el ``.exe``.

    Fuentes, en orden (la última gana, con ``override=True``):
      1. ``.envx`` embebido en el bundle: el ``.env`` codificado que la spec de
         PyInstaller incrusta al construir. Permite distribuir SOLO el ``.exe``
         (autocontenido) sin dejar las credenciales en texto plano.
      2. ``.env`` en texto plano embebido (compatibilidad), si existiera.
      3. ``.env`` EXTERNO, junto al ejecutable o en el directorio de trabajo
         (desarrollo). Tiene prioridad, así se pueden sobreescribir credenciales
         dejando un ``.env`` al lado del ``.exe`` sin reempaquetar.
    """
    try:
        from dotenv import load_dotenv
    except Exception:  # noqa: BLE001 — sin dotenv se usa os.environ tal cual
        return

    # 1) .envx ofuscado embebido.
    envx = resource_path(".envx")
    if os.path.exists(envx):
        try:
            import io
            with open(envx, "rb") as fh:
                contenido = _desofuscar_env(fh.read())
            load_dotenv(stream=io.StringIO(contenido), override=True)
        except Exception:  # noqa: BLE001 — si el blob es inválido, se ignora
            pass

    # 2) .env plano embebido (compat).
    embebido = resource_path(".env")
    if os.path.exists(embebido):
        load_dotenv(dotenv_path=embebido, override=True)

    # 2.5) MACRO/.env: las credenciales de SQL Server / Portal / SharePoint
    # viven aquí (separadas del ORACLE_* de la raíz). En el .exe ya vienen
    # fusionadas en el .envx; esto cubre DESARROLLO (correr desde el código), donde
    # de lo contrario faltarían las DB_* y la BD interna volvería vacía. La ruta se
    # resuelve relativa al módulo (no a cwd) para no depender del directorio actual.
    macro_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(macro_env):
        load_dotenv(dotenv_path=macro_env, override=True)

    # 3) .env externo (desarrollo / junto al .exe), tiene prioridad.
    if getattr(sys, "frozen", False):
        externo = os.path.join(os.path.dirname(sys.executable), ".env")
    else:
        externo = os.path.join(os.getcwd(), ".env")
    if os.path.exists(externo) and os.path.abspath(externo) != os.path.abspath(embebido):
        load_dotenv(dotenv_path=externo, override=True)

def _valor_a_texto(valor):
    """Convierte cualquier valor a texto normalizado para comparación y despliegue."""
    if isinstance(valor, str):
        texto = valor.strip()
        return "" if texto.lower() in {"nan", "none"} else texto

    if valor is None or pd.isna(valor):  # type: ignore[arg-type]
        return ""

    if isinstance(valor, float):
        if not math.isfinite(valor):
            return ""
        if valor.is_integer():
            return str(int(valor))
        texto = f"{valor:.10f}".rstrip('0').rstrip('.')
        return texto

    return str(valor).strip()

def _normalizar_texto_numerico(texto):
    """Devuelve una representación estandarizada si el texto es numérico, o None en caso contrario."""
    if not texto:
        return None

    texto = texto.strip()
    if not texto:
        return None

    signo = ""
    resto = texto
    if resto[0] in "+-":
        if resto[0] == "-":
            signo = "-"
        resto = resto[1:]

    if not resto:
        return None

    if resto.count('.') > 1 or resto.count(',') > 1:
        return None

    if '.' in resto and ',' in resto:
        return None

    if '.' in resto:
        partes = resto.split('.', 1)
        if len(partes) != 2 or not partes[0] or not partes[1]:
            return None
        entero, decimal = partes
        if not (entero.isdigit() and decimal.isdigit()):
            return None
        valor_decimal = f"{signo}{entero}.{decimal}"
    elif ',' in resto:
        partes = resto.split(',', 1)
        if len(partes) != 2 or not partes[0] or not partes[1]:
            return None
        entero, decimal = partes
        if not (entero.isdigit() and decimal.isdigit()):
            return None
        valor_decimal = f"{signo}{entero}.{decimal}"
    else:
        if not resto.isdigit():
            return None
        valor_decimal = f"{signo}{resto}"

    try:
        numero = Decimal(valor_decimal)
    except (InvalidOperation, ValueError):
        return None

    if numero == numero.to_integral():
        return str(int(numero))

    texto_normalizado = format(numero.normalize(), 'f').rstrip('0').rstrip('.')
    return texto_normalizado or "0"

def _normalizar_texto_para_comparacion(texto):
    """Normaliza texto para comparaciones, preservando valores no numéricos."""
    if not texto:
        return ""

    texto_numerico = _normalizar_texto_numerico(texto)
    return texto_numerico if texto_numerico is not None else texto

def _formatear_cambio(valor_anterior, valor_nuevo):
    anterior = _valor_a_texto(valor_anterior)
    nuevo = _valor_a_texto(valor_nuevo)
    return f"{anterior} → {nuevo}".strip()

def _preparar_registros_para_comparacion(df, columnas, columna_clave):
    registros_valores = {}
    registros_comparacion = {}
    orden = []
    for _, row in df.iterrows():
        clave = _valor_a_texto(row.get(columna_clave))
        if not clave:
            continue
        if clave not in registros_valores:
            orden.append(clave)

        fila_valores = {}
        fila_comparacion = {}
        for col in columnas:
            valor_texto = _valor_a_texto(row.get(col))
            fila_valores[col] = valor_texto
            fila_comparacion[col] = _normalizar_texto_para_comparacion(valor_texto)

        registros_valores[clave] = fila_valores
        registros_comparacion[clave] = fila_comparacion

    return registros_valores, registros_comparacion, orden

def _normalize_numeric_value(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    text = str(value).strip()
    if not text:
        return None

    replacements = {
        "S/": "",
        "s/": "",
        "\u00a0": "",
        "\u202f": "",
        " ": "",
        "'": "",
        "−": "-",
        "–": "-",
        ")": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("(", "-")
    if text.endswith('-') and text.count('-') == 1:
        text = '-' + text[:-1]

    if not text:
        return None

    comma_count = text.count(',')
    dot_count = text.count('.')
    if comma_count and dot_count:
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.', '')
            text = text.replace(',', '.')
        else:
            text = text.replace(',', '')
    elif comma_count and not dot_count:
        text = text.replace(',', '.')
    else:
        text = text.replace(',', '')

    try:
        return Decimal(text)
    except InvalidOperation:
        try:
            return Decimal(text.replace('.', ''))
        except InvalidOperation:
            return None

def _coerce_to_number(value):
    result = _normalize_numeric_value(value)
    if result is None:
        return None
    return float(result)

def _is_empty_row(row):
    for value in row:
        if value is None:
            continue
        if isinstance(value, float):
            if math.isnan(value):
                continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return False
    return True

def _sum_numeric_values(values):
    total = Decimal('0')
    has_value = False
    for value in values:
        numeric = _normalize_numeric_value(value)
        if numeric is not None:
            total += numeric
            has_value = True
    return float(total) if has_value else 0.0

def _archivo_esta_bloqueado(ruta):
    """
    Verifica si un archivo está siendo usado por otro proceso.
    Retorna True si está bloqueado/abierto, False si está disponible.
    """
    try:
        # Intenta abrir el archivo en modo exclusivo
        with open(ruta, 'r+b') as f:
            pass
        return False
    except IOError:
        return True
    except Exception:
        # Si no existe o hay otro error, asumimos que no está bloqueado por uso
        # (o que no se puede acceder, pero para efectos de "está abierto en Excel" sirve)
        return False

def extraer_anio(per_doc):
    # Soporta 2023, 202312, '2023-12', '2023/12', etc.
    m = re.search(r'(\d{4})', str(per_doc))
    return int(m.group(1)) if m else None

