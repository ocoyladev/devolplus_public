"""Operaciones de administración de accesos (usadas por ``admin_accesos``).

Reutiliza la conexión Oracle del módulo compartido. Devuelve dicts para que la
capa web (FastAPI) los serialice directamente a JSON.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from MACRO.auth.db_connection import get_connection

# Estados válidos para una decisión administrativa.
ESTADOS_VALIDOS = ("aprobado", "rechazado", "inactivo", "pendiente")

# registro_logueos.fecha_hora se llena con SYSTIMESTAMP y la Autonomous Database
# corre en UTC, así que lo almacenado es hora universal. El historial se muestra
# en hora de Perú: UTC-5 fijo, sin horario de verano.
ZONA_PERU = timezone(timedelta(hours=-5))


def _iso(valor: Any) -> Any:
    """Convierte datetimes a ISO string; deja el resto tal cual."""
    return valor.isoformat() if hasattr(valor, "isoformat") else valor


def _iso_hora_peru(valor: Any) -> Any:
    """ISO string en UTC-5. Un datetime sin zona se interpreta como UTC (es lo
    que devuelve la columna TIMESTAMP); lo que no sea datetime pasa intacto."""
    if not isinstance(valor, datetime):
        return _iso(valor)
    con_zona = valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    return con_zona.astimezone(ZONA_PERU).isoformat()


def listar_solicitudes(estado: str | None = None) -> list[dict[str, Any]]:
    """Lista usuarios; si ``estado`` se indica, filtra por él."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            base = """
                SELECT id, nombre_completo, usuario_red, email, estado,
                       fecha_solicitud, fecha_revision, aprobado_por, observaciones
                FROM usuarios
            """
            if estado:
                cur.execute(base + " WHERE estado = :1 ORDER BY fecha_solicitud", [estado])
            else:
                cur.execute(base + " ORDER BY fecha_solicitud DESC")
            cols = [d[0].lower() for d in cur.description]
            return [
                {c: _iso(v) for c, v in zip(cols, row)} for row in cur.fetchall()
            ]
    finally:
        conn.close()


def actualizar_estado(
    usuario_id: int,
    nuevo_estado: str,
    admin_actual: str,
    observaciones: str | None = None,
) -> dict[str, Any]:
    """Aprueba/rechaza/inactiva un usuario y deja traza de la revisión."""
    if nuevo_estado not in ESTADOS_VALIDOS:
        return {"ok": False, "mensaje": f"Estado inválido: {nuevo_estado}"}
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE usuarios
                SET estado = :1, fecha_revision = SYSTIMESTAMP,
                    aprobado_por = :2, observaciones = :3
                WHERE id = :4
                """,
                [nuevo_estado, admin_actual, observaciones, usuario_id],
            )
            afectados = cur.rowcount
        conn.commit()
        if not afectados:
            return {"ok": False, "mensaje": "Usuario no encontrado."}
        return {"ok": True, "mensaje": f"Usuario actualizado a '{nuevo_estado}'."}
    finally:
        conn.close()


def historial_logueos(
    usuario_red: str | None = None, limite: int = 50
) -> list[dict[str, Any]]:
    """Historial de logueos, opcionalmente filtrado por usuario."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if usuario_red:
                cur.execute(
                    """
                    SELECT u.usuario_red, l.fecha_hora, l.resultado, l.ip_maquina,
                           l.version
                    FROM registro_logueos l
                    JOIN usuarios u ON u.id = l.usuario_id
                    WHERE u.usuario_red = :1
                    ORDER BY l.fecha_hora DESC
                    FETCH FIRST :2 ROWS ONLY
                    """,
                    [usuario_red, limite],
                )
            else:
                cur.execute(
                    """
                    SELECT u.usuario_red, l.fecha_hora, l.resultado, l.ip_maquina,
                           l.version
                    FROM registro_logueos l
                    JOIN usuarios u ON u.id = l.usuario_id
                    ORDER BY l.fecha_hora DESC
                    FETCH FIRST :1 ROWS ONLY
                    """,
                    [limite],
                )
            cols = [d[0].lower() for d in cur.description]
            return [
                {c: (_iso_hora_peru(v) if c == "fecha_hora" else _iso(v))
                 for c, v in zip(cols, row)}
                for row in cur.fetchall()
            ]
    finally:
        conn.close()
