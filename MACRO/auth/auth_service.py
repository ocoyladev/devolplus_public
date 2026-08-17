"""Servicio de autenticación/auditoría sobre Oracle + caché local.

Orquesta el flujo de arranque de la web app:

* Online: valida el usuario en ``usuarios``, audita en ``registro_logueos`` y
  cachea la aprobación. Vacía oportunamente la cola de logueos pendientes.
* Offline (Oracle caído): deja entrar a quien la caché local recuerde como
  ``aprobado`` (encolando el logueo) y deniega a los demás.
"""
from __future__ import annotations

import getpass
import os
import re
import socket
from datetime import datetime
from typing import Any

from MACRO.auth import cache_local
from MACRO.auth.db_connection import get_connection
from MACRO.version import get_version

# Modo de autenticación. ``oracle`` consulta la base corporativa de accesos;
# ``demo`` (por defecto en esta distribución) aprueba a cualquier usuario sin
# base de datos, para que la aplicación se pueda ejecutar y evaluar sin
# infraestructura. Ver README > "Modo demo".
AUTH_MODE = os.environ.get("AUTH_MODE", "demo").strip().lower()

# Identificador sintético del usuario en modo demo (no existe en ninguna base).
DEMO_USUARIO_ID = 1

# Dominio de correo exigido para autoregistrarse. Configurable por entorno para
# no fijar ninguna organización en el código.
EMAIL_ORG_DOMAIN = os.environ.get("AUTH_EMAIL_DOMAIN", "example.org")
EMAIL_ORG_RE = re.compile(r"^[a-z0-9._%+-]+@" + re.escape(EMAIL_ORG_DOMAIN) + r"$")

# Mapeo estado del usuario -> resultado auditado en registro_logueos.
_RESULTADO_DENEGADO = {
    "pendiente": "denegado_pendiente",
    "rechazado": "denegado_rechazado",
    "inactivo": "denegado_inactivo",
}

_MENSAJES = {
    "no_registrado": (
        "No tiene acceso registrado. Complete la solicitud para pedir "
        "autorización a el administrador."
    ),
    "pendiente": (
        "Su solicitud está pendiente de autorización. Contacte a el administrador."
    ),
    "rechazado": (
        "Su solicitud fue rechazada. Contacte a el administrador para más información."
    ),
    "inactivo": "Su acceso está inactivo. Contacte a el administrador para reactivarlo.",
    "sin_conexion": (
        "No se pudo verificar el acceso (sin conexión a la base de datos) y no "
        "cuenta con autorización previa en este equipo. Reintente más tarde o "
        "contacte a el administrador."
    ),
    "permitido": "Acceso autorizado.",
}


def obtener_usuario_red() -> str:
    """Usuario de Windows normalizado (minúsculas), como en seguridad.py."""
    try:
        usuario = os.getlogin()
    except Exception:  # noqa: BLE001 — fallback fuera de una sesión interactiva
        usuario = getpass.getuser()
    return usuario.strip().lower()


def _ip_maquina() -> str | None:
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:  # noqa: BLE001 — la IP es opcional para la auditoría
        return None


# --- Operaciones directas sobre Oracle -------------------------------------

def validar_usuario(usuario_red: str, conn=None) -> tuple[int, str] | None:
    """Devuelve ``(id, estado)`` del usuario o ``None`` si no existe.

    Reutiliza ``conn`` si se pasa (evita abrir una segunda conexión durante el
    arranque); en caso contrario abre y cierra la suya.
    """
    propia = conn is None
    if propia:
        conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, estado FROM usuarios WHERE usuario_red = :1",
                [usuario_red],
            )
            row = cur.fetchone()
            return (int(row[0]), row[1]) if row else None
    finally:
        if propia:
            conn.close()


def solicitar_acceso(
    nombre_completo: str, usuario_red: str, email: str
) -> dict[str, Any]:
    """Autoregistro: INSERT en ``usuarios`` con estado ``pendiente``.

    El correo es obligatorio y debe pertenecer a ``EMAIL_ORG_DOMAIN``; se
    valida aquí para devolver un mensaje claro (no un 422 de Pydantic).
    """
    nombre = (nombre_completo or "").strip()
    if not nombre:
        return {"ok": False, "mensaje": "El nombre completo es obligatorio."}
    email_norm = (email or "").strip().lower()
    if not EMAIL_ORG_RE.match(email_norm):
        return {
            "ok": False,
            "mensaje": f"Ingrese un correo institucional válido (…@{EMAIL_ORG_DOMAIN}).",
        }

    # En demo no hay tabla de solicitudes: el acceso ya está concedido, así que
    # se acusa recibo sin persistir nada.
    if AUTH_MODE == "demo":
        return {
            "ok": True,
            "mensaje": "Modo demostración: el acceso está concedido, no hace falta solicitarlo.",
        }

    import oracledb  # import diferido para el manejo de IntegrityError

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO usuarios (nombre_completo, usuario_red, email)
                VALUES (:1, :2, :3)
                """,
                [nombre, usuario_red, email_norm],
            )
        conn.commit()
        return {
            "ok": True,
            "mensaje": "Solicitud registrada. Queda pendiente de autorización.",
        }
    except oracledb.IntegrityError:
        return {
            "ok": False,
            "mensaje": "Este usuario ya tiene una solicitud registrada.",
        }
    finally:
        conn.close()


def registrar_logueo(
    conn,
    usuario_id: int,
    resultado: str,
    ip_maquina: str | None,
    fecha_hora: datetime | None = None,
    version: str | None = None,
) -> None:
    """INSERT en ``registro_logueos`` usando la conexión Oracle dada.

    Si ``fecha_hora`` es ``None`` usa el ``SYSTIMESTAMP`` de Oracle; si se pasa
    (logueos encolados) se inserta ese instante real. ``version`` es la versión
    del aplicativo usada en ese logueo (columna ``version``).
    """
    version = version or get_version()
    with conn.cursor() as cur:
        if fecha_hora is None:
            cur.execute(
                """
                INSERT INTO registro_logueos (usuario_id, resultado, ip_maquina, version)
                VALUES (:1, :2, :3, :4)
                """,
                [usuario_id, resultado, ip_maquina, version],
            )
        else:
            cur.execute(
                """
                INSERT INTO registro_logueos
                    (usuario_id, resultado, ip_maquina, fecha_hora, version)
                VALUES (:1, :2, :3, :4, :5)
                """,
                [usuario_id, resultado, ip_maquina, fecha_hora, version],
            )
    conn.commit()


def flush_pendientes(conn) -> int:
    """Sube a Oracle los logueos encolados. Devuelve cuántos se enviaron."""
    enviados = 0
    for pend in cache_local.listar_pendientes():
        registrar_logueo(
            conn,
            pend["usuario_id"],
            pend["resultado"],
            pend["ip_maquina"],
            fecha_hora=pend["fecha_hora_local"],
            version=pend.get("version"),
        )
        cache_local.borrar_pendiente(pend["id"])
        enviados += 1
    return enviados


# --- Orquestación del arranque ---------------------------------------------

def verificar_acceso(usuario_red: str | None = None) -> dict[str, Any]:
    """Resuelve el acceso al arrancar la app.

    Devuelve ``{estado, usuario_red, usuario_id?, nombre?, mensaje}`` donde
    ``estado`` es uno de: ``permitido``, ``no_registrado``, ``pendiente``,
    ``rechazado``, ``inactivo``, ``sin_conexion``.
    """
    usuario_red = usuario_red or obtener_usuario_red()
    ip = _ip_maquina()
    cache_local.ensure_tablas_auth()  # idempotente; caché/cola disponibles

    # Modo demostración: no hay base de datos corporativa que consultar, así que
    # todo usuario queda aprobado. Sigue registrándose el logueo en la caché
    # local para que el panel de administración tenga datos que mostrar.
    if AUTH_MODE == "demo":
        cache_local.upsert_aprobado(usuario_red, DEMO_USUARIO_ID)
        cache_local.encolar_logueo(
            DEMO_USUARIO_ID, "exitoso", ip, datetime.now(), get_version()
        )
        return _respuesta("permitido", usuario_red, usuario_id=DEMO_USUARIO_ID)

    try:
        conn = get_connection()
    except Exception:  # noqa: BLE001 — sin conexión: caemos a la caché local
        return _resolver_offline(usuario_red, ip)

    try:
        flush_pendientes(conn)
        resultado = validar_usuario(usuario_red, conn)
        if resultado is None:
            return _respuesta("no_registrado", usuario_red)

        usuario_id, estado = resultado
        if estado == "aprobado":
            registrar_logueo(conn, usuario_id, "exitoso", ip)
            cache_local.upsert_aprobado(usuario_red, usuario_id)
            return _respuesta("permitido", usuario_red, usuario_id=usuario_id)

        registrar_logueo(conn, usuario_id, _RESULTADO_DENEGADO[estado], ip)
        return _respuesta(estado, usuario_red, usuario_id=usuario_id)
    finally:
        conn.close()


def _resolver_offline(usuario_red: str, ip: str | None) -> dict[str, Any]:
    cacheado = cache_local.get(usuario_red)
    if cacheado and cacheado["estado"] == "aprobado":
        cache_local.encolar_logueo(
            cacheado["usuario_id"], "exitoso", ip, datetime.now(), get_version()
        )
        return _respuesta("permitido", usuario_red, usuario_id=cacheado["usuario_id"])
    return _respuesta("sin_conexion", usuario_red)


def _respuesta(
    estado: str, usuario_red: str, usuario_id: int | None = None
) -> dict[str, Any]:
    return {
        "estado": estado,
        "usuario_red": usuario_red,
        "usuario_id": usuario_id,
        "mensaje": _MENSAJES[estado],
    }
