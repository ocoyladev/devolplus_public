"""Conexión a Oracle Autonomous Database (modo *thin*, sin Instant Client).

Las credenciales y la ruta del wallet se leen del ``.env`` (nunca hardcodeadas),
siguiendo el mismo patrón que ``MACRO/funciones/funciones_bd.py``. El import de
``oracledb`` es diferido para que el resto del paquete se pueda importar (y
testear con mocks) aunque el driver o el wallet no estén presentes.
"""
from __future__ import annotations

import concurrent.futures
import os

from MACRO.funciones.funciones_generales import cargar_env

# Carga del .env (embebido o externo junto al .exe) una sola vez al importar.
cargar_env()

# Tope (segundos) para abrir la conexión a Oracle. Sin esto, si la Autonomous DB
# no es alcanzable (sin internet / red que no rutea al cloud) el connect se queda
# colgado varios minutos (el descriptor _tp reintenta ~20 veces), dejando la
# pantalla de logueo esperando. Con el tope, el connect falla rápido y
# ``verificar_acceso`` cae a la caché local (usuario ya aprobado entra offline).
# Configurable por .env (ORACLE_CONNECT_TIMEOUT).
_CONNECT_TIMEOUT_S = float(os.getenv("ORACLE_CONNECT_TIMEOUT", "20"))


class ConfigIncompletaError(RuntimeError):
    """Faltan variables de entorno para conectar a Oracle."""


def _leer_config() -> dict[str, str]:
    # Prefijo ORACLE_ para no colisionar con las variables DB_* de SQL Server
    # que ya usa MACRO/funciones/funciones_bd.py.
    faltantes = [
        v
        for v in ("ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_DSN")
        if not os.getenv(v)
    ]
    if faltantes:
        raise ConfigIncompletaError(
            "Faltan variables de conexión Oracle en .env: " + ", ".join(faltantes)
        )
    return {
        "user": os.environ["ORACLE_USER"],
        "password": os.environ["ORACLE_PASSWORD"],
        "dsn": os.environ["ORACLE_DSN"],
    }


def get_connection():
    """Abre una conexión Oracle thin a la Autonomous DB por TLS (sin wallet).

    El DSN es el connect descriptor completo con ``protocol=tcps`` y
    ``ssl_server_dn_match=yes`` (alias ``_tp``), así que no hace falta wallet ni
    Instant Client. Lanza ``ConfigIncompletaError`` si falta configuración y
    propaga los errores de ``oracledb`` (p. ej. ``DatabaseError`` si la BD está
    detenida/inaccesible), que el orquestador interpreta como "sin conexión".
    """
    import oracledb  # import diferido: el driver solo se necesita aquí

    cfg = _leer_config()

    def _do_connect():
        # tcp_connect_timeout + retry_count acotan el intento a nivel del driver;
        # el tope de reloj de abajo garantiza el límite pase lo que pase el
        # descriptor DSN (algunos alias _tp embeben retry_count=20/retry_delay=3).
        return oracledb.connect(
            user=cfg["user"],
            password=cfg["password"],
            dsn=cfg["dsn"],
            tcp_connect_timeout=_CONNECT_TIMEOUT_S,
            retry_count=0,
            retry_delay=0,
        )

    # Tope de reloj duro: si el connect no responde en _CONNECT_TIMEOUT_S se
    # abandona el hilo (que morirá solo al vencer tcp_connect_timeout) y se lanza
    # TimeoutError para que el orquestador caiga a la caché local.
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=1, thread_name_prefix="oracle-connect"
    )
    future = executor.submit(_do_connect)
    try:
        conn = future.result(timeout=_CONNECT_TIMEOUT_S)
        executor.shutdown(wait=False)
        return conn
    except concurrent.futures.TimeoutError as exc:
        executor.shutdown(wait=False)  # no cancela el hilo colgado; solo deja de esperarlo
        raise TimeoutError(
            f"Timeout ({_CONNECT_TIMEOUT_S:.0f}s) conectando a Oracle"
        ) from exc
    except BaseException:
        executor.shutdown(wait=False)
        raise
