import sqlite3
import os
import pandas as pd
from datetime import datetime
import hashlib
import base64
import sys
from io import StringIO

from .funciones.funciones_generales import (
    COLUMNAS_FECHA_DB,
    formatear_ddmmyyyy,
    normalizar_columnas_fecha,
    parsear_columnas_fecha,
)

# Versión del esquema/normalización de fechas. Si subes este número se vuelve
# a ejecutar la migración de fechas (idempotente).
MIGRACION_FECHAS_VERSION = "1"

def get_db_path():
    if getattr(sys, 'frozen', False):
        # Si está ejecutándose como un ejecutable (.exe)
        return os.path.join(os.path.dirname(sys.executable), "devol_plus.db")
    else:
        # Si es un script (.py) normal
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "devol_plus.db")

# DB_FILE = "devol_plus.db"
DB_FILE = get_db_path()
# _MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_FILE = os.path.join(_MODULE_DIR, "devol_plus.db")

# Columnas "extra" (añadidas/no provenientes del Excel) que deben existir en
# tabla_asign y su versión _archivo. Añadir aquí futuras columnas nuevas.
COLUMNAS_EXTRA = {
    "adeudos_aplicar": "TEXT DEFAULT '0.00'",
    "exp_echasqui": "TEXT DEFAULT ''",
}


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def actualizar_esquema_db():
    """Garantiza que las columnas de COLUMNAS_EXTRA existan en tabla_asign y
    tabla_asign_archivo (si existen). Idempotente."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for tabla in ("tabla_asign", "tabla_asign_archivo"):
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (tabla,),
            )
            if not cursor.fetchone():
                continue
            cursor.execute(f"PRAGMA table_info({tabla})")
            existentes = {col["name"] for col in cursor.fetchall()}
            for col, tipo in COLUMNAS_EXTRA.items():
                if col not in existentes:
                    try:
                        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}")
                        conn.commit()
                        print(f"Migración: columna '{col}' agregada a {tabla}.")
                    except Exception as e:  # noqa: BLE001
                        print(f"Error agregando '{col}' a {tabla}: {e}")
    finally:
        conn.close()

    # tabla_cartas: DDL + backfill una sola vez desde el espejo tabla_asign.carta.
    try:
        from MACRO.funciones.funciones_registro_cartas import (
            backfill_desde_espejo, crear_tabla_cartas,
        )

        crear_tabla_cartas()
        conn = get_db_connection()
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY, valor TEXT)"
            )
            conn.commit()
        finally:
            conn.close()
        if obtener_config("cartas_backfill_v1") != "1":
            creadas = backfill_desde_espejo()
            guardar_config("cartas_backfill_v1", "1")
            if creadas:
                print(f"Migración: {creadas} carta(s) migradas a tabla_cartas.")
    except Exception as e:  # noqa: BLE001
        print(f"Error migrando tabla_cartas: {e}")

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tabla de credenciales cifradas
    c.execute('''
        CREATE TABLE IF NOT EXISTS credenciales (
            sistema TEXT PRIMARY KEY,
            usuario TEXT,
            password_hash TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de asignaciones (flujo por Excel)
    c.execute('''
        CREATE TABLE IF NOT EXISTS tabla_asign (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            carta TEXT,
            resultado TEXT,
            int_fecha_inicial TEXT,
            int_fecha_final TEXT,
            int_importe TEXT,
            int_valor TEXT,
            adeudos_aplicar TEXT,
            exp_echasqui TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de tracking de descargas por documento
    c.execute('''
        CREATE TABLE IF NOT EXISTS descargas_tracking (
            num_doc TEXT PRIMARY KEY,
            total_descargas INTEGER DEFAULT 0,
            descargas_ok INTEGER DEFAULT 0,
            descargas_pendientes TEXT,  -- JSON array con detalles de descargas pendientes
            estado TEXT DEFAULT 'pendiente',  -- pendiente, en_proceso, completado, error
            ultimo_error TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla de configuracion
    c.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
    ''')

    # Tabla de datos de BD remota (cruzada con asignaciones)
    c.execute('''
        CREATE TABLE IF NOT EXISTS tabla_bd (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Based on inferred columns and user requirements
    c.execute('''
        CREATE TABLE IF NOT EXISTS registros (
            num_doc TEXT PRIMARY KEY,
            of_devolucion TEXT,
            num_ruc TEXT,
            nombre TEXT,
            periodo TEXT,
            cod_sol TEXT,
            cod_for TEXT,
            cod_for_aso TEXT,
            ind_dev TEXT,
            vcto_ind TEXT,
            
            -- Columns requested by user
            carta TEXT,
            fecha_carta TEXT,
            ri TEXT,
            fecha_ri TEXT,
            
            -- Extra columns from source
            auditor_responsable TEXT,
            direccion TEXT,
            departamento TEXT,
            provincia TEXT,
            distrito TEXT,
            cod_tri TEXT,
            fec_doc TEXT,
            mto_solicitado TEXT,
            num_doc_aso TEXT,
            resultado TEXT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de descargas individualizadas (Nueva estructura)
    c.execute('''
        CREATE TABLE IF NOT EXISTS tabla_desc (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_doc TEXT,
            ruc TEXT,
            tipo_servicio TEXT,   -- 'PORTAL', 'WORKFLOW', 'BD', 'UNKNOWN'
            tipo_descarga TEXT,   -- 'PLANEAMIENTO', 'FORMULARIO', 'PERSONALIZADO', '3UIT', 'RXH', 'ITF', 'EXP_ELECTRONICO', 'OF', 'DOCUMENTOS'
            parametro TEXT,       -- RUC, Numero OF, Numero Formulario, etc.
            ruta_destino TEXT,
            estado TEXT DEFAULT 'PENDIENTE', -- 'PENDIENTE', 'EN_PROCESO', 'EXITO', 'ERROR', 'OMITIDO'
            reintentos INTEGER DEFAULT 0,
            error_log TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla de días no laborables (feriados) definidos por el usuario
    c.execute('''
        CREATE TABLE IF NOT EXISTS dias_no_laborables (
            fecha TEXT PRIMARY KEY
        )
    ''')

    # Cola de archivado de expedientes ECHASQUI (conclusión ATENDIDO).
    c.execute('''
        CREATE TABLE IF NOT EXISTS tabla_archivar_echasqui (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_doc TEXT, ruc TEXT, num_ri TEXT,
            aduana TEXT, urd TEXT, anio TEXT, nroexpedi TEXT, denom TEXT,
            estado TEXT DEFAULT 'pendiente', mensaje TEXT DEFAULT '',
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(num_doc, aduana, urd, anio, nroexpedi)
        )
    ''')

    conn.commit()
    conn.close()

    actualizar_esquema_db()
    migrar_fechas_db()


def migrar_fechas_db(forzar: bool = False) -> dict:
    """Normaliza las columnas de fecha de tabla_asign / tabla_bd y sus _archivo
    a string "DD/MM/YYYY". Idempotente: usa la clave `migracion_fechas_version`
    en la tabla `configuracion` para correr una sola vez por versión.

    Args:
        forzar: Si True, ignora la versión guardada y re-ejecuta la migración.

    Returns:
        dict con `ejecutada`, `tablas_actualizadas`, `total_filas` y `mensaje`.
    """
    version_actual = obtener_config("migracion_fechas_version")
    if not forzar and version_actual == MIGRACION_FECHAS_VERSION:
        return {
            "ejecutada": False,
            "tablas_actualizadas": [],
            "total_filas": 0,
            "mensaje": "Migración de fechas ya estaba al día.",
        }

    conn = get_db_connection()
    tablas_objetivo = ("tabla_asign", "tabla_bd", "tabla_asign_archivo", "tabla_bd_archivo")
    tablas_actualizadas = []
    total_filas = 0
    try:
        cursor = conn.cursor()
        for tabla in tablas_objetivo:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
            )
            if not cursor.fetchone():
                continue

            cursor.execute(f"PRAGMA table_info({tabla})")
            cols_existentes = [row[1] for row in cursor.fetchall()]
            cols_fecha = [c for c in COLUMNAS_FECHA_DB if c in cols_existentes]
            if not cols_fecha:
                continue

            filas_actualizadas = 0
            for col in cols_fecha:
                cursor.execute(
                    f'SELECT rowid, "{col}" FROM {tabla} WHERE "{col}" IS NOT NULL AND TRIM("{col}") != ""'
                )
                for rowid, valor in cursor.fetchall():
                    nuevo = formatear_ddmmyyyy(valor)
                    nuevo = nuevo if nuevo else None
                    if (valor or "").strip() != (nuevo or ""):
                        cursor.execute(
                            f'UPDATE {tabla} SET "{col}" = ? WHERE rowid = ?',
                            (nuevo, rowid),
                        )
                        filas_actualizadas += 1

            if filas_actualizadas:
                tablas_actualizadas.append((tabla, filas_actualizadas))
                total_filas += filas_actualizadas
                print(
                    f"✓ Migración fechas: {tabla} → {filas_actualizadas} celdas normalizadas"
                )

        conn.commit()
    except Exception as e:
        print(f"Error en migrar_fechas_db: {e}")
        conn.rollback()
        return {
            "ejecutada": False,
            "tablas_actualizadas": tablas_actualizadas,
            "total_filas": total_filas,
            "mensaje": f"Error: {e}",
        }
    finally:
        conn.close()

    guardar_config("migracion_fechas_version", MIGRACION_FECHAS_VERSION)
    return {
        "ejecutada": True,
        "tablas_actualizadas": tablas_actualizadas,
        "total_filas": total_filas,
        "mensaje": (
            f"Migración completada: {total_filas} celdas normalizadas en "
            f"{len(tablas_actualizadas)} tabla(s)."
            if total_filas
            else "Migración completada: no se requerían cambios."
        ),
    }

def importar_desde_excel(excel_path):
    """
    Reads the 'Reporte_nueva_data.xlsx' and imports into SQLite.
    Comparasion by 'num_doc'. New records are added.
    """
    if not os.path.exists(excel_path):
        return 0

    try:
        df = pd.read_excel(excel_path, dtype=str)
    except Exception as e:
        print(f"Error leyendo excel: {e}")
        return 0

    conn = get_db_connection()
    c = conn.cursor()
    
    nuevo_count = 0
    
    # Map DataFrame columns to Table columns
    # We normalized names in valid_columns to match likely DF headers
    # Logic: iterate rows, check if num_doc exists, if not insert.
    
    for _, row in df.iterrows():
        num_doc = str(row.get('num_doc', '')).strip()
        if not num_doc or num_doc == 'nan':
            continue
            
        # Check existence
        c.execute("SELECT 1 FROM registros WHERE num_doc = ?", (num_doc,))
        if c.fetchone():
            continue
        
        # Insert
        # We need to map row keys to our table columns safely
        of_devolucion = row.get('of_devolucion', '')
        num_ruc = row.get('num_ruc', '')
        # Handle 'ddp_nombre' or 'nombre'
        nombre = row.get('ddp_nombre', row.get('nombre', ''))
        periodo = row.get('per_doc', row.get('periodo', ''))
        cod_sol = row.get('cod_tip_sol', row.get('cod_sol', ''))
        cod_for = row.get('cod_for', '')
        cod_for_aso = row.get('cod_for_aso', '')
        ind_dev = row.get('ind_dev', '') # Might need calculation if not in excel
        vcto_ind = row.get('vcto_ind', '') # Might need calculation
        auditor = row.get('Auditor responsable', '')
        
        # Extra fields
        direccion = row.get('direccion', '')
        departamento = row.get('departamento', '')
        provincia = row.get('provincia', '')
        distrito = row.get('distrito', '')
        cod_tri = row.get('cod_tri', '')
        fec_doc = row.get('fec_doc', '')
        mto_solicitado = row.get('mto_solicitado', '')
        num_doc_aso = row.get('num_doc_aso', '')

        # Insert query
        c.execute('''
            INSERT INTO registros (
                num_doc, of_devolucion, num_ruc, nombre, periodo, 
                cod_sol, cod_for, cod_for_aso, ind_dev, vcto_ind, 
                auditor_responsable, direccion, departamento, provincia, distrito,
                cod_tri, fec_doc, mto_solicitado, num_doc_aso
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            num_doc, of_devolucion, num_ruc, nombre, periodo,
            cod_sol, cod_for, cod_for_aso, ind_dev, vcto_ind,
            auditor, direccion, departamento, provincia, distrito,
            cod_tri, fec_doc, mto_solicitado, num_doc_aso
        ))
        nuevo_count += 1

    conn.commit()
    conn.close()
    return nuevo_count

def obtener_todos():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM registros ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    
    # Convert Row objects to dicts
    result = []
    for row in rows:
        result.append(dict(row))
    return result

def esta_vacia():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM registros")
    count = c.fetchone()[0]
    conn.close()
    return count == 0

# --- Funciones para Credenciales Cifradas ---
#
# NOTA: esto es ofuscación reversible, no cifrado fuerte. La clave se lee del
# entorno para que el repositorio no la contenga. Ver README > "Limitaciones
# conocidas": para almacenamiento real de secretos usar el keyring del SO.


def _clave_xor() -> str:
    """Clave de ofuscación. Configurable por entorno; el default es de demo."""
    return os.environ.get("DEVOL_XOR_KEY", "demo-xor-key")


def _cifrar_password(password: str) -> str:
    """Cifra la contraseña usando XOR con clave fija (cifrado reversible simple)."""
    if not password:
        return ""
    clave = _clave_xor()
    
    # Cifrar usando XOR
    cifrado = []
    for i, char in enumerate(password):
        key_char = clave[i % len(clave)]
        cifrado.append(chr(ord(char) ^ ord(key_char)))
    
    # Codificar en base64 para almacenamiento seguro
    resultado = ''.join(cifrado)
    return base64.b64encode(resultado.encode('latin-1')).decode('utf-8')

def _descifrar_password(password_cifrado: str) -> str:
    """Descifra la contraseña usando XOR con clave fija."""
    if not password_cifrado:
        return ""
    
    try:
        # Decodificar desde base64
        cifrado = base64.b64decode(password_cifrado).decode('latin-1')
        
        clave = _clave_xor()
        
        # Descifrar usando XOR (mismo proceso que cifrado)
        descifrado = []
        for i, char in enumerate(cifrado):
            key_char = clave[i % len(clave)]
            descifrado.append(chr(ord(char) ^ ord(key_char)))
        
        return ''.join(descifrado)
    except Exception:
        return ""

def guardar_credenciales(sistema: str, usuario: str, password: str):
    """Guarda o actualiza las credenciales de un sistema."""
    conn = get_db_connection()
    c = conn.cursor()
    
    password_hash = _cifrar_password(password)
    
    c.execute('''
        INSERT OR REPLACE INTO credenciales (sistema, usuario, password_hash, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (sistema, usuario, password_hash))
    
    conn.commit()
    conn.close()

def obtener_credenciales(sistema: str, incluir_password: bool = False) -> dict:
    """Obtiene las credenciales de un sistema.
    
    Args:
        sistema: Nombre del sistema ('Portal' o 'Workflow')
        incluir_password: Si True, descifra y devuelve la contraseña
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    if incluir_password:
        c.execute("SELECT usuario, password_hash, updated_at FROM credenciales WHERE sistema = ?", (sistema,))
    else:
        c.execute("SELECT usuario, updated_at FROM credenciales WHERE sistema = ?", (sistema,))
    
    row = c.fetchone()
    conn.close()
    
    if row:
        resultado = {
            'usuario': row[0],
            'tiene_password': True,
            'updated_at': row[-1]
        }
        if incluir_password and len(row) > 2:
            resultado['password'] = _descifrar_password(row[1])
        return resultado
    
    return {
        'usuario': '',
        'tiene_password': False,
        'updated_at': None,
        'password': '' if incluir_password else None
    }


# --- Funciones para flujo de asignación (Excel) ---

def persistir_tabla_asign(df):
    """
    Persiste DataFrame de asignación en tabla_asign usando columnas reales.
    Utiliza pandas to_sql para recrear la tabla con la estructura del DataFrame.
    IMPORTANTE: Normaliza todas las columnas de fecha a "DD/MM/YYYY" antes de persistir
    (vía funciones_generales.normalizar_columnas_fecha, que maneja DD/MM/YYYY,
    YYYY-MM-DD y datetimes nativos sin invertir día/mes).
    """
    conn = get_db_connection()
    try:
        df_to_save = df.copy()

        normalizar_columnas_fecha(df_to_save)

        for col in ['num_doc_aso', 'num_dev', 'num_ri', 'num_doc', 'ruc', 'num_ruc']:
            if col in df_to_save.columns:
                df_to_save[col] = df_to_save[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

        df_to_save.to_sql('tabla_asign', conn, if_exists='replace', index=False)

        print(f"✓ tabla_asign persistida correctamente con {len(df_to_save)} registros")
    except Exception as e:
        print(f"Error persistiendo tabla_asign: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


def obtener_tabla_asign():
    """
    Obtiene el DataFrame de asignación desde tabla_asign via SQL directo.
    Las columnas de fecha se devuelven como `pd.Timestamp` (vía
    funciones_generales.parsear_columnas_fecha) para que la GUI/Excel reciban
    objetos datetime nativos.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tabla_asign';")
        if not cursor.fetchone():
            return None

        df = pd.read_sql("SELECT * FROM tabla_asign", conn)
        parsear_columnas_fecha(df)
        return df
    except Exception as e:
        print(f"Error obteniendo tabla_asign: {e}")
        return None
    finally:
        conn.close()


def obtener_tabla_asign_incluye_archivo():
    """Como ``obtener_tabla_asign`` pero une ``tabla_asign_archivo`` (casos
    archivados). Ante ``num_doc`` duplicado, gana la fila activa. Usado por
    'Generar PPTT' para operar también sobre casos archivados."""
    df = obtener_tabla_asign()
    if df is None:
        df = pd.DataFrame()

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tabla_asign_archivo';")
        if not cur.fetchone():
            return df
        df_arch = pd.read_sql("SELECT * FROM tabla_asign_archivo", conn)
    except Exception:
        return df
    finally:
        conn.close()

    if df_arch is None or df_arch.empty:
        return df
    if df is None or df.empty:
        return df_arch

    activos = set(df["num_doc"].astype(str).str.strip())
    df_arch = df_arch[~df_arch["num_doc"].astype(str).str.strip().isin(activos)]
    if df_arch.empty:
        return df
    return pd.concat([df, df_arch], ignore_index=True)


def persistir_tabla_bd(df):
    """
    Persiste DataFrame de BD remota en tabla_bd usando columnas reales.
    Todas las columnas de fecha se normalizan a "DD/MM/YYYY" antes de persistir.
    """
    conn = get_db_connection()
    try:
        df_to_save = df.copy()
        normalizar_columnas_fecha(df_to_save)

        df_to_save.to_sql('tabla_bd', conn, if_exists='replace', index=False)
        print(f"✓ tabla_bd persistida correctamente con {len(df_to_save)} registros")
    except Exception as e:
        print(f"Error persistiendo tabla_bd: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


def obtener_tabla_bd():
    """
    Obtiene el DataFrame de BD desde tabla_bd. Las columnas de fecha se
    devuelven como `pd.Timestamp` (vía parsear_columnas_fecha), aceptando
    indistintamente DD/MM/YYYY y YYYY-MM-DD por compatibilidad histórica.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tabla_bd';")
        if not cursor.fetchone():
            return None

        df = pd.read_sql("SELECT * FROM tabla_bd", conn)
        parsear_columnas_fecha(df)
        return df
    except Exception as e:
        print(f"Error obteniendo tabla_bd: {e}")
        return None
    finally:
        conn.close()


def limpiar_tablas_asignacion():
    """
    Limpia todas las tablas de datos (asignación, BD y registros antiguos).
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("DELETE FROM tabla_asign")
    c.execute("DELETE FROM tabla_bd")
    c.execute("DELETE FROM registros")
    c.execute("DELETE FROM descargas_tracking")

    # tabla_cartas es la fuente de verdad de las cartas (ver borrar_caso); si no
    # se limpia aquí, un re-import tras "Borrar BD" muestra cartas huérfanas.
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tabla_cartas'")
    if c.fetchone():
        c.execute("DELETE FROM tabla_cartas")

    conn.commit()
    conn.close()


# --- Funciones para tracking de descargas ---

def inicializar_tracking_descarga(num_doc, total_descargas):
    """
    Inicializa el tracking de descargas para un documento.
    
    Args:
        num_doc: Número de documento
        total_descargas: Total de descargas esperadas
    """
    import json
    
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        INSERT OR REPLACE INTO descargas_tracking 
        (num_doc, total_descargas, descargas_ok, descargas_pendientes, estado, updated_at)
        VALUES (?, ?, 0, ?, 'pendiente', CURRENT_TIMESTAMP)
    ''', (num_doc, total_descargas, json.dumps([])))
    
    conn.commit()
    conn.close()


def actualizar_descarga_exitosa(num_doc, tipo_descarga):
    """
    Actualiza el contador de descargas exitosas.
    
    Args:
        num_doc: Número de documento
        tipo_descarga: Tipo de descarga completada (ej: 'portal_personalizado')
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # Incrementar contador
    c.execute('''
        UPDATE descargas_tracking 
        SET descargas_ok = descargas_ok + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE num_doc = ?
    ''', (num_doc,))
    
    # Verificar si se completó todo
    c.execute('''
        SELECT descargas_ok, total_descargas 
        FROM descargas_tracking 
        WHERE num_doc = ?
    ''', (num_doc,))
    
    row = c.fetchone()
    if row and row[0] >= row[1]:
        c.execute('''
            UPDATE descargas_tracking 
            SET estado = 'completado'
            WHERE num_doc = ?
        ''', (num_doc,))
    
    conn.commit()
    conn.close()


def registrar_descarga_pendiente(num_doc, tipo_descarga, params, error=None):
    """
    Registra una descarga pendiente por fallo.
    
    Args:
        num_doc: Número de documento
        tipo_descarga: Tipo de descarga (ej: 'portal_3uit')
        params: Diccionario con parámetros de la descarga
        error: Mensaje de error opcional
    """
    import json
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Obtener lista actual de pendientes
    c.execute('SELECT descargas_pendientes FROM descargas_tracking WHERE num_doc = ?', (num_doc,))
    row = c.fetchone()
    
    pendientes = []
    if row and row[0]:
        try:
            pendientes = json.loads(row[0])
        except:
            pendientes = []
    
    # Agregar nueva descarga pendiente
    pendientes.append({
        'tipo': tipo_descarga,
        'params': params,
        'error': error
    })
    
    # Actualizar BD
    c.execute('''
        UPDATE descargas_tracking 
        SET descargas_pendientes = ?,
            estado = 'error',
            ultimo_error = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE num_doc = ?
    ''', (json.dumps(pendientes), error, num_doc))
    
    conn.commit()
    conn.close()


def obtener_tracking_descarga(num_doc):
    """
    Obtiene el estado de tracking de un documento.
    
    Returns:
        dict con total_descargas, descargas_ok, estado, etc.
    """
    import json
    
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT total_descargas, descargas_ok, descargas_pendientes, estado, ultimo_error
        FROM descargas_tracking 
        WHERE num_doc = ?
    ''', (num_doc,))
    
    row = c.fetchone()
    conn.close()
    
    if row:
        pendientes = []
        try:
            if row[2]:
                pendientes = json.loads(row[2])
        except:
            pass
        
        return {
            'total_descargas': row[0],
            'descargas_ok': row[1],
            'descargas_pendientes': pendientes,
            'estado': row[3],
            'ultimo_error': row[4]
        }
    
    return None


def obtener_todas_pendientes():
    """
    Obtiene todos los documentos con descargas pendientes.
    
    Returns:
        Lista de dicts con información de descargas pendientes
    """
    import json
    
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT num_doc, total_descargas, descargas_ok, descargas_pendientes, ultimo_error
        FROM descargas_tracking 
        WHERE estado = 'error' AND descargas_pendientes != '[]'
    ''')
    
    rows = c.fetchall()
    conn.close()
    
    resultado = []
    for row in rows:
        pendientes = []
        try:
            if row[3]:
                pendientes = json.loads(row[3])
        except:
            pass
        
        resultado.append({
            'num_doc': row[0],
            'total_descargas': row[1],
            'descargas_ok': row[2],
            'descargas_pendientes': pendientes,
            'ultimo_error': row[4]
        })
    
    return resultado

# --- Funciones para TABLA_DESC (Nueva gesti�n de cola) ---

def registrar_descarga_individual(num_doc, servicio, tipo, parametro, ruta_destino, ruc=None):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Migración "lazy": Asegurar columna ruc
    try:
        c.execute('SELECT ruc FROM tabla_desc LIMIT 1')
    except sqlite3.OperationalError:
        try:
            c.execute('ALTER TABLE tabla_desc ADD COLUMN ruc TEXT')
            conn.commit()
        except:
            pass
            
    # Verificar si ya existe un registro no completado (cualquier estado salvo
    # 'EXITO'). Si existe, se REACTIVA a 'PENDIENTE' en lugar de omitirlo: de lo
    # contrario una descarga que quedó en 'ERROR'/'EN_PROCESO' nunca volvería a
    # procesarse (procesar_descargas_bd solo toma 'PENDIENTE') y se quedaría
    # colgada esperando indefinidamente.
    c.execute('''
        SELECT id FROM tabla_desc
        WHERE num_doc = ? AND tipo_descarga = ? AND parametro = ? AND estado != 'EXITO'
    ''', (num_doc, tipo, parametro))
    existent = c.fetchone()

    if existent:
        c.execute('''
            UPDATE tabla_desc
            SET estado = 'PENDIENTE', error_log = '', ruta_destino = ?, ruc = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (ruta_destino, ruc, existent[0]))
    else:
        c.execute('''
            INSERT INTO tabla_desc (num_doc, ruc, tipo_servicio, tipo_descarga, parametro, ruta_destino, estado, reintentos)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDIENTE', 0)
        ''', (num_doc, ruc, servicio, tipo, parametro, ruta_destino))
    conn.commit()
    conn.close()

def obtener_descargas_pendientes_bd():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Migración "lazy" por si acaso
    try:
        c.execute('SELECT ruc FROM tabla_desc LIMIT 1')
    except sqlite3.OperationalError:
        try:
            c.execute('ALTER TABLE tabla_desc ADD COLUMN ruc TEXT')
            conn.commit()
        except:
            pass

    # Ordenar por RUC para permitir procesamiento lineal por contribuyente
    c.execute('''
        SELECT * FROM tabla_desc 
        WHERE estado = 'PENDIENTE'
        ORDER BY ruc, tipo_servicio, id
    ''')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def actualizar_estado_descarga_bd(id_descarga, nuevo_estado, error_msg=None):
    conn = get_db_connection()
    c = conn.cursor()
    
    extra_sql = ', reintentos = reintentos + 1' if nuevo_estado == 'ERROR' else ''
    error_val = error_msg if error_msg else ''
    
    c.execute(f'''
        UPDATE tabla_desc 
        SET estado = ?, error_log = ?, updated_at = CURRENT_TIMESTAMP {extra_sql}
        WHERE id = ?
    ''', (nuevo_estado, error_val, id_descarga))
    conn.commit()
    conn.close()

def limpiar_tabla_desc_bd():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM tabla_desc')
    conn.commit()
    conn.close()

def obtener_descargas_bd(solo_pendientes=False):
    """Lista las descargas de la cola para su gestión (todas las no completadas).

    Devuelve dicts con id, num_doc, ruc, tipo_servicio, tipo_descarga, parametro,
    estado, reintentos y error_log. Con ``solo_pendientes=True`` restringe a las
    que están en 'PENDIENTE'.
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute('SELECT ruc FROM tabla_desc LIMIT 1')
    except sqlite3.OperationalError:
        try:
            c.execute('ALTER TABLE tabla_desc ADD COLUMN ruc TEXT')
            conn.commit()
        except Exception:
            pass

    if solo_pendientes:
        c.execute(
            "SELECT id, num_doc, ruc, tipo_servicio, tipo_descarga, parametro, "
            "estado, reintentos, error_log FROM tabla_desc "
            "WHERE estado = 'PENDIENTE' ORDER BY ruc, tipo_servicio, id"
        )
    else:
        c.execute(
            "SELECT id, num_doc, ruc, tipo_servicio, tipo_descarga, parametro, "
            "estado, reintentos, error_log FROM tabla_desc "
            "WHERE estado != 'EXITO' ORDER BY ruc, tipo_servicio, id"
        )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def eliminar_descargas_bd(ids):
    """Elimina de la cola las descargas cuyos id estén en ``ids``. Devuelve cuántas."""
    ids = [int(i) for i in (ids or [])]
    if not ids:
        return 0
    conn = get_db_connection()
    c = conn.cursor()
    placeholders = ','.join('?' * len(ids))
    c.execute(f'DELETE FROM tabla_desc WHERE id IN ({placeholders})', ids)
    count = c.rowcount
    conn.commit()
    conn.close()
    return count

def reactivar_descargas_bd(ids):
    """Reactiva a 'PENDIENTE' las descargas indicadas por ``ids``. Devuelve cuántas."""
    ids = [int(i) for i in (ids or [])]
    if not ids:
        return 0
    conn = get_db_connection()
    c = conn.cursor()
    placeholders = ','.join('?' * len(ids))
    c.execute(
        f"UPDATE tabla_desc SET estado = 'PENDIENTE', error_log = '', "
        f"updated_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders})",
        ids,
    )
    count = c.rowcount
    conn.commit()
    conn.close()
    return count

def resetear_errores_descarga_bd():
    """
    Reactiva a 'PENDIENTE' las descargas reanudables: las fallidas ('ERROR')
    y las que quedaron huérfanas en 'EN_PROCESO' por una interrupción del
    proceso (cierre de la app, corte, etc.). Como las descargas se ejecutan
    de forma secuencial, cualquier fila 'EN_PROCESO' al reintentar está
    necesariamente obsoleta. Devuelve el número de filas reactivadas.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE tabla_desc SET estado = 'PENDIENTE', reintentos = reintentos + 1 WHERE estado IN ('ERROR', 'EN_PROCESO')")
    count = c.rowcount
    conn.commit()
    conn.close()
    return count


def contar_descargas_pendientes_bd():
    """Devuelve el número de descargas en estado 'PENDIENTE'."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tabla_desc WHERE estado = 'PENDIENTE'")
    count = c.fetchone()[0]
    conn.close()
    return count


# --- Cola de archivado ECHASQUI -------------------------------------------

def crear_tabla_archivar_echasqui():
    """Crea la cola de archivado echasqui si no existe (idempotente)."""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tabla_archivar_echasqui (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_doc TEXT, ruc TEXT, num_ri TEXT,
            aduana TEXT, urd TEXT, anio TEXT, nroexpedi TEXT, denom TEXT,
            estado TEXT DEFAULT 'pendiente', mensaje TEXT DEFAULT '',
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(num_doc, aduana, urd, anio, nroexpedi)
        )
    ''')
    conn.commit()
    conn.close()


def upsert_archivar_echasqui(item):
    """Inserta un pendiente; si ya existe la clave (num_doc,aduana,urd,anio,
    nroexpedi) lo reactiva a 'pendiente'. Devuelve el id de la fila."""
    crear_tabla_archivar_echasqui()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO tabla_archivar_echasqui
            (num_doc, ruc, num_ri, aduana, urd, anio, nroexpedi, denom, estado, mensaje)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', '')
        ON CONFLICT(num_doc, aduana, urd, anio, nroexpedi) DO UPDATE SET
            ruc=excluded.ruc, num_ri=excluded.num_ri, denom=excluded.denom,
            estado='pendiente', mensaje=''
    ''', (item.get("num_doc"), item.get("ruc"), item.get("num_ri"),
          item.get("aduana"), item.get("urd"), item.get("anio"),
          item.get("nroexpedi"), item.get("denom")))
    conn.commit()
    c.execute('''SELECT id FROM tabla_archivar_echasqui
                 WHERE num_doc=? AND aduana=? AND urd=? AND anio=? AND nroexpedi=?''',
              (item.get("num_doc"), item.get("aduana"), item.get("urd"),
               item.get("anio"), item.get("nroexpedi")))
    row = c.fetchone()
    conn.close()
    return int(row[0]) if row else -1


def listar_archivar_echasqui():
    """Lista todos los pendientes de archivado echasqui."""
    crear_tabla_archivar_echasqui()
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT id, num_doc, ruc, num_ri, aduana, urd, anio, nroexpedi,
                        denom, estado, mensaje, fecha_registro
                 FROM tabla_archivar_echasqui ORDER BY num_doc, id''')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def marcar_archivar_echasqui_error(id_fila, mensaje):
    """Marca un pendiente como 'error' con su motivo."""
    conn = get_db_connection()
    conn.execute("UPDATE tabla_archivar_echasqui SET estado='error', mensaje=? WHERE id=?",
                 (str(mensaje)[:500], int(id_fila)))
    conn.commit()
    conn.close()


def marcar_archivar_echasqui_pendiente(id_fila, mensaje):
    """Marca un pendiente como 'pendiente' con su motivo (no lo elimina)."""
    conn = get_db_connection()
    conn.execute("UPDATE tabla_archivar_echasqui SET estado='pendiente', mensaje=? WHERE id=?",
                 (str(mensaje)[:500], int(id_fila)))
    conn.commit()
    conn.close()


def eliminar_archivar_echasqui(ids):
    """Elimina los pendientes cuyos id estén en ``ids``. Devuelve cuántos."""
    ids = [int(i) for i in (ids or [])]
    if not ids:
        return 0
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"DELETE FROM tabla_archivar_echasqui WHERE id IN ({','.join('?'*len(ids))})", ids)
    n = c.rowcount
    conn.commit()
    conn.close()
    return n


def borrar_archivar_echasqui():
    """Vacía la cola de archivado echasqui."""
    conn = get_db_connection()
    conn.execute("DELETE FROM tabla_archivar_echasqui")
    conn.commit()
    conn.close()


def actualizar_dato_celda(tabla, col_name, valor, num_doc):
    """
    Actualiza un dato específico en una tabla, creando la columna si no existe.
    
    Args:
        tabla (str): Nombre de la tabla ('tabla_asign' o 'tabla_bd')
        col_name (str): Nombre de la columna a actualizar
        valor (str): Nuevo valor
        num_doc (str): Identificador del documento (num_doc)
    """
    # Validar tabla para evitar inyección o errores, añadimos 'registros' por si acaso
    if tabla not in ['tabla_asign', 'tabla_bd', 'registros',
                     'tabla_asign_archivo', 'tabla_bd_archivo']:
        print(f"Tabla no permitida: {tabla}")
        return False
        
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 1. Verificar si existe la tabla
        c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabla}'")
        if not c.fetchone():
            print(f"La tabla {tabla} no existe")
            return False

        # 2. Verificar si existe la columna
        c.execute(f"PRAGMA table_info({tabla})")
        columns = [row[1] for row in c.fetchall()]
        
        if col_name not in columns:
            print(f"Columna {col_name} no existe en {tabla}. Creándola...")
            try:
                # SQLite permite ALTER TABLE ADD COLUMN
                c.execute(f"ALTER TABLE {tabla} ADD COLUMN {col_name} TEXT")
                conn.commit()
            except Exception as e:
                print(f"Error creando columna: {e}")
                return False
        
        # 3. Actualizar el valor
        query = f"UPDATE {tabla} SET {col_name} = ? WHERE num_doc = ?"
        c.execute(query, (str(valor), str(num_doc)))
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error actualizando celda: {e}")
        return False
    finally:
        conn.close()


# --- Funciones de Configuración y Archivo (Nuevas) ---

def guardar_config(clave, valor):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (clave, valor))
        conn.commit()
    except Exception as e:
        print(f"Error guardando config {clave}: {e}")
    finally:
        conn.close()

def obtener_config(clave, default=None):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
        row = c.fetchone()
        return row['valor'] if row else default
    except Exception as e:
        # print(f"Error leyendo config {clave}: {e}")
        return default
    finally:
        conn.close()

def archivar_casos_db(lista_num_doc):
    """
    Mueve registros de tabla_bd y tabla_asign a sus versiones _archivo.
    Verifica dinámicamente las columnas de la tabla destino y agrega las faltantes
    antes de insertar (soluciona "no such column" error).
    Retorna cantidad de registros movidos (basado en tabla_bd).
    """
    if not lista_num_doc:
        return 0

    def _asegurar_columnas_destino(conn, tabla_origen, tabla_destino, df_origen):
        """
        Verifica que la tabla destino (_archivo) tenga todas las columnas
        del DataFrame origen. Si faltan columnas, las crea con ALTER TABLE.
        """
        cursor = conn.cursor()
        
        # Verificar si la tabla destino existe
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabla_destino}';")
        if not cursor.fetchone():
            # La tabla no existe; to_sql la creará automáticamente
            return
        
        # Obtener columnas existentes en tabla destino
        cursor.execute(f"PRAGMA table_info({tabla_destino})")
        cols_destino = set(col[1] for col in cursor.fetchall())
        
        # Obtener columnas del DataFrame origen
        cols_origen = set(df_origen.columns.tolist())
        
        # Agregar columnas faltantes
        cols_faltantes = cols_origen - cols_destino
        for col in cols_faltantes:
            try:
                cursor.execute(f"ALTER TABLE {tabla_destino} ADD COLUMN [{col}] TEXT")
                print(f"  Columna '{col}' agregada a {tabla_destino}")
            except Exception as e:
                print(f"  Error agregando columna '{col}' a {tabla_destino}: {e}")
        
        if cols_faltantes:
            conn.commit()

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tabla_bd';")
        has_bd = cursor.fetchone() is not None
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tabla_asign';")
        has_asign = cursor.fetchone() is not None
        
        if not has_bd and not has_asign:
            return 0
            
        count_moved = 0
        
        # Procesar tabla_bd
        if has_bd:
            cursor.execute("PRAGMA table_info(tabla_bd)")
            cols = [col[1] for col in cursor.fetchall()]
            if 'num_doc' in cols:
                df_bd = pd.read_sql("SELECT * FROM tabla_bd", conn)
                mask = df_bd['num_doc'].astype(str).str.strip().isin(lista_num_doc)
                rows_to_move = df_bd[mask]
                
                if not rows_to_move.empty:
                    # Asegurar columnas en tabla destino ANTES de insertar
                    _asegurar_columnas_destino(conn, 'tabla_bd', 'tabla_bd_archivo', rows_to_move)
                    rows_to_move.to_sql('tabla_bd_archivo', conn, if_exists='append', index=False)
                    count_moved = len(rows_to_move)
                    
                    placeholders = ','.join(['?'] * len(lista_num_doc))
                    conn.execute(f"DELETE FROM tabla_bd WHERE num_doc IN ({placeholders})", lista_num_doc)
        
        # Procesar tabla_asign
        if has_asign:
            cursor.execute("PRAGMA table_info(tabla_asign)")
            cols = [col[1] for col in cursor.fetchall()]
            if 'num_doc' in cols:
                df_asign = pd.read_sql("SELECT * FROM tabla_asign", conn)
                mask = df_asign['num_doc'].astype(str).str.strip().isin(lista_num_doc)
                rows_to_move = df_asign[mask]
                
                if not rows_to_move.empty:
                    # Asegurar columnas en tabla destino ANTES de insertar
                    _asegurar_columnas_destino(conn, 'tabla_asign', 'tabla_asign_archivo', rows_to_move)
                    rows_to_move.to_sql('tabla_asign_archivo', conn, if_exists='append', index=False)
                    placeholders = ','.join(['?'] * len(lista_num_doc))
                    conn.execute(f"DELETE FROM tabla_asign WHERE num_doc IN ({placeholders})", lista_num_doc)

        conn.commit()
        return count_moved

    except Exception as e:
        print(f"Error archivando casos: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

def recuperar_casos_db(lista_num_doc):
    """
    Mueve registros de tabla_bd_archivo y tabla_asign_archivo hacia tabla_bd y tabla_asign.
    Retorna la cantidad de registros recuperados.
    """
    if not lista_num_doc:
        return 0

    def _asegurar_columnas_destino(conn, tabla_origen, tabla_destino, df_origen):
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabla_destino}';")
        if not cursor.fetchone():
            return
        cursor.execute(f"PRAGMA table_info({tabla_destino})")
        cols_destino = set(col[1] for col in cursor.fetchall())
        cols_origen = set(df_origen.columns.tolist())
        cols_faltantes = cols_origen - cols_destino
        for col in cols_faltantes:
            try:
                cursor.execute(f"ALTER TABLE {tabla_destino} ADD COLUMN [{col}] TEXT")
            except Exception:
                pass
        if cols_faltantes:
            conn.commit()

    import pandas as pd
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tabla_bd_archivo';")
        has_bd = cursor.fetchone() is not None
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tabla_asign_archivo';")
        has_asign = cursor.fetchone() is not None
        
        if not has_bd and not has_asign:
            return 0
            
        count_moved = 0
        
        # Procesar tabla_bd_archivo -> tabla_bd
        if has_bd:
            cursor.execute("PRAGMA table_info(tabla_bd_archivo)")
            cols = [col[1] for col in cursor.fetchall()]
            if 'num_doc' in cols:
                df_bd = pd.read_sql("SELECT * FROM tabla_bd_archivo", conn)
                mask = df_bd['num_doc'].astype(str).str.strip().isin(lista_num_doc)
                rows_to_move = df_bd[mask]
                
                if not rows_to_move.empty:
                    _asegurar_columnas_destino(conn, 'tabla_bd_archivo', 'tabla_bd', rows_to_move)
                    rows_to_move.to_sql('tabla_bd', conn, if_exists='append', index=False)
                    count_moved = len(rows_to_move)
                    placeholders = ','.join(['?'] * len(lista_num_doc))
                    conn.execute(f"DELETE FROM tabla_bd_archivo WHERE num_doc IN ({placeholders})", lista_num_doc)
        
        # Procesar tabla_asign_archivo -> tabla_asign
        if has_asign:
            cursor.execute("PRAGMA table_info(tabla_asign_archivo)")
            cols = [col[1] for col in cursor.fetchall()]
            if 'num_doc' in cols:
                df_asign = pd.read_sql("SELECT * FROM tabla_asign_archivo", conn)
                mask = df_asign['num_doc'].astype(str).str.strip().isin(lista_num_doc)
                rows_to_move = df_asign[mask]
                
                if not rows_to_move.empty:
                    _asegurar_columnas_destino(conn, 'tabla_asign_archivo', 'tabla_asign', rows_to_move)
                    rows_to_move.to_sql('tabla_asign', conn, if_exists='append', index=False)
                    placeholders = ','.join(['?'] * len(lista_num_doc))
                    conn.execute(f"DELETE FROM tabla_asign_archivo WHERE num_doc IN ({placeholders})", lista_num_doc)

        conn.commit()
        return count_moved

    except Exception as e:
        print(f"Error recuperando casos: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()


_TABLAS_CASO_BORRADO = [
    "tabla_asign", "tabla_bd", "tabla_asign_archivo", "tabla_bd_archivo", "tabla_desc",
    "tabla_cartas",
]


def borrar_caso(num_doc: str) -> dict:
    """Hard-delete de un caso por ``num_doc`` en las tablas de caso + cola de
    descargas. Irreversible (no archiva). Devuelve {tabla: filas_borradas}."""
    num_doc = str(num_doc or "").strip()
    eliminadas = {t: 0 for t in _TABLAS_CASO_BORRADO}
    if not num_doc:
        return eliminadas
    conn = get_db_connection()
    try:
        c = conn.cursor()
        for t in _TABLAS_CASO_BORRADO:
            c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,))
            if not c.fetchone():
                continue
            cols = [col[1] for col in c.execute(f"PRAGMA table_info({t})").fetchall()]
            if "num_doc" not in cols:
                continue
            cur = c.execute(f"DELETE FROM {t} WHERE num_doc = ?", (num_doc,))
            eliminadas[t] = cur.rowcount
        conn.commit()
        return eliminadas
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# --- Funciones para Días No Laborables (Feriados) ---

def agregar_feriado(fecha: str):
    """Agrega un día no laborable. Formato esperado: 'YYYY-MM-DD'."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO dias_no_laborables (fecha) VALUES (?)", (fecha,))
        conn.commit()
    except Exception as e:
        print(f"Error agregando feriado: {e}")
    finally:
        conn.close()

def eliminar_feriado(fecha: str):
    """Elimina un día no laborable. Formato esperado: 'YYYY-MM-DD'."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM dias_no_laborables WHERE fecha = ?", (fecha,))
        conn.commit()
    except Exception as e:
        print(f"Error eliminando feriado: {e}")
    finally:
        conn.close()

def obtener_feriados() -> list:
    """Retorna lista de strings con las fechas de días no laborables (formato 'YYYY-MM-DD')."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT fecha FROM dias_no_laborables ORDER BY fecha")
        rows = c.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        print(f"Error obteniendo feriados: {e}")
        return []
    finally:
        conn.close()


def obtener_datos_para_envio(lista_num_doc):
    """
    Obtiene registros de tabla_bd y tabla_asign para la lista de documentos.
    Retorna un DataFrame con la info unificada o la de BD.
    """
    conn = get_db_connection()
    try:
        # Check structure for num_doc
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tabla_bd)")
        cols = [col[1] for col in cursor.fetchall()]

        if 'num_doc' not in cols:
            return pd.DataFrame()
        
        df = pd.read_sql("SELECT * FROM tabla_bd", conn)
        mask = df['num_doc'].astype(str).str.strip().isin(lista_num_doc)
        return df[mask]
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def obtener_datos_incluye_archivo(lista_num_doc):
    """Como ``obtener_datos_para_envio`` pero, para los num_doc que no estén en
    ``tabla_bd``, cae de vuelta a ``tabla_bd_archivo`` (casos archivados).

    Pensado para flujos que también deben operar sobre casos archivados (p. ej.
    verificar echasqui electrónico). NO altera ``obtener_datos_para_envio``, que
    debe seguir viendo solo casos activos.
    """
    lista = [str(d).strip() for d in (lista_num_doc or []) if str(d).strip()]
    if not lista:
        return pd.DataFrame()

    df = obtener_datos_para_envio(lista)
    encontrados = set()
    if df is not None and not df.empty:
        encontrados = set(df['num_doc'].astype(str).str.strip())
    faltantes = [d for d in lista if d not in encontrados]
    if not faltantes:
        return df

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tabla_bd_archivo';")
        if not cursor.fetchone():
            return df
        cursor.execute("PRAGMA table_info(tabla_bd_archivo)")
        cols = [col[1] for col in cursor.fetchall()]
        if 'num_doc' not in cols:
            return df
        df_arch = pd.read_sql("SELECT * FROM tabla_bd_archivo", conn)
        mask = df_arch['num_doc'].astype(str).str.strip().isin(faltantes)
        df_arch = df_arch[mask]
    except Exception:
        return df
    finally:
        conn.close()

    if df_arch.empty:
        return df
    if df is None or df.empty:
        return df_arch
    return pd.concat([df, df_arch], ignore_index=True)



def dato_asign(num_doc, columna):
    """Valor de ``columna`` en tabla_asign para ``num_doc`` (activa → archivo).

    Existe porque ``obtener_datos_para_envio`` sirve las filas desde ``tabla_bd``,
    que NO es la fuente de verdad de varias columnas: ``exp_echasqui`` solo vive
    en tabla_asign, y ``num_dev`` se rellena ahí (flujo_sync hace el backfill
    tabla_bd → tabla_asign, nunca al revés), de modo que en tabla_bd puede
    quedar vacío indefinidamente.

    Devuelve '' si no hay valor, si la tabla/columna no existe o si el caso no
    está. Nunca lanza.
    """
    num_doc = str(num_doc or "").strip()
    columna = str(columna or "").strip()
    if not num_doc or not columna.isidentifier():
        return ""
    conn = get_db_connection()
    try:
        for tabla in ("tabla_asign", "tabla_asign_archivo"):
            c = conn.cursor()
            c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,))
            if not c.fetchone():
                continue
            cols = [col[1] for col in c.execute(f"PRAGMA table_info({tabla})").fetchall()]
            if columna not in cols or "num_doc" not in cols:
                continue
            fila = c.execute(
                f"SELECT {columna} FROM {tabla} WHERE trim(num_doc) = ? LIMIT 1",
                (num_doc,)).fetchone()
            if fila and str(fila[0] or "").strip():
                return str(fila[0]).strip()
    except Exception:  # noqa: BLE001 — un dato ausente nunca debe tumbar el flujo
        return ""
    finally:
        conn.close()
    return ""


def num_docs_archivados(lista_num_doc):
    """Devuelve los num_doc de la lista que YA están en el archivo (tabla_asign_archivo)."""
    if not lista_num_doc:
        return []
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tabla_asign_archivo'"
        )
        if not c.fetchone():
            return []
        docs = [str(x).strip() for x in lista_num_doc]
        placeholders = ",".join(["?"] * len(docs))
        c.execute(
            f"SELECT num_doc FROM tabla_asign_archivo WHERE num_doc IN ({placeholders})",
            docs,
        )
        return sorted({str(r[0]).strip() for r in c.fetchall()})
    finally:
        conn.close()
