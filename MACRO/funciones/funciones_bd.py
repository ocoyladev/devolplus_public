import os
import pandas as pd
from .funciones_generales import cargar_env

# Carga el .env (embebido en el bundle o externo junto al .exe).
cargar_env()

# Timeout (segundos) para abrir la conexión a la BD interna (SQL Server). Evita
# que la app se quede colgada varios minutos si la red institucional no está
# disponible (p. ej. tras un cambio de red). Configurable por .env.
_DB_CONNECT_TIMEOUT = int(os.getenv('DB_CONNECT_TIMEOUT', '20'))


class ConexionBDInternaError(RuntimeError):
    """No se pudo abrir la conexión con la BD interna (SQL Server).

    Se distingue de un resultado vacío: significa "sin conexión", no "no hay
    filas". Los flujos que la propagan (p. ej. el cruce de asignación) pueden
    así abortar con un mensaje claro en vez de caer al fallback con datos
    incompletos.
    """


def _diagnostico_conexion(ex) -> str:
    """Traduce el SQLSTATE de un error pyodbc a una causa accionable.

    Sirve para que el usuario sepa QUÉ arreglar (driver, red, credenciales) en
    vez de un "no se pudo conectar" genérico. El SQLSTATE viene en ``ex.args[0]``.
    """
    sqlstate = str(ex.args[0]).upper() if getattr(ex, "args", None) else ""
    if sqlstate.startswith("IM"):  # IM002/IM001/IM003: driver/DSN ODBC ausente
        return (
            f"[{sqlstate}] No se encontró el driver ODBC de SQL Server en este "
            "equipo. Instálalo (p. ej. 'ODBC Driver 17 for SQL Server') y "
            "verifica que DB_DRIVER en .env coincida con su nombre exacto."
        )
    if sqlstate == "28000":  # login inválido
        return (
            f"[{sqlstate}] Usuario o contraseña inválidos para la BD interna "
            "(revisa DB_USERNAME / DB_PASSWORD en .env)."
        )
    if sqlstate.startswith("08") or sqlstate in ("HYT00", "HYT01"):  # red/servidor/timeout
        return (
            f"[{sqlstate}] No se pudo alcanzar el servidor de la BD interna. "
            "Verifica la red/VPN, el firewall y que DB_SERVER en .env sea correcto."
        )
    return f"[{sqlstate or 'sin SQLSTATE'}] {ex}"


def obtener_datos_filtrados(lista_num_doc, raise_on_conn_error: bool = False):
    """Conecta a la BD y descarga los datos filtrados por la lista de num_doc.

    Args:
        lista_num_doc: documentos a consultar.
        raise_on_conn_error: si es ``True``, un fallo *de conexión* (BD interna
            inaccesible) lanza :class:`ConexionBDInternaError` en vez de
            devolver ``None``. Los errores de *consulta* y el resultado vacío
            siguen devolviendo ``None`` (comportamiento histórico que respetan
            el resto de los llamadores).
    """
    import pyodbc  # import diferido: el driver SQL Server solo se necesita aquí

    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_DATABASE')
    username = os.getenv('DB_USERNAME')
    password = os.getenv('DB_PASSWORD')
    driver = os.getenv('DB_DRIVER')

    if not all([server, database, username, password, driver]):
        print("Error: Faltan variables de entorno en el archivo .env.")
        if raise_on_conn_error:
            raise ConexionBDInternaError(
                "Faltan variables de conexión a la BD interna en .env."
            )
        return None

    connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    placeholders = ','.join(['?'] * len(lista_num_doc))
    sql_query = f"""
        SELECT *
        FROM [db_fisca_exp].[rep].[dev_resultado_ppnn_danc]
        WHERE num_doc IN ({placeholders})
    """

    # Abrir la conexión (acotada por timeout) por separado de la consulta para
    # poder distinguir "sin conexión" de "error de consulta / sin filas".
    try:
        print("Conectando a la base de datos...")
        cnxn = pyodbc.connect(connection_string, timeout=_DB_CONNECT_TIMEOUT)
    except pyodbc.Error as ex:
        diagnostico = _diagnostico_conexion(ex)
        print(f"Error de conexión a la BD interna: {diagnostico}")
        if raise_on_conn_error:
            raise ConexionBDInternaError(diagnostico) from ex
        return None

    try:
        with cnxn:
            dataframe = pd.read_sql_query(sql_query, cnxn, params=lista_num_doc)
            print(f"¡Conexión y descarga de BD exitosa! Se encontraron {len(dataframe)} filas.")
            return dataframe if not dataframe.empty else None
    except pyodbc.Error as ex:
        # Error de consulta (no de conexión): se conserva el comportamiento
        # previo (se trata como "sin datos"), independiente de raise_on_conn_error.
        print(f"Error de consulta a la BD: {ex.args[0] if ex.args else ''}\n{ex}")
        return None
