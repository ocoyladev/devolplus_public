"""Caché local de autorización + cola de logueos pendientes.

Vive en el mismo SQLite del aplicativo (``devol_plus.db`` via
``MACRO.database.get_db_connection``). Cubre el caso "Oracle no responde":

* ``auth_cache``: recuerda la última vez que Oracle confirmó a un usuario como
  ``aprobado``; permite dejar entrar offline a quien ya fue autorizado antes.
* ``logueos_pendientes``: logueos que no se pudieron insertar en Oracle; se
  vacían con ``MACRO.auth.auth_service.flush_pendientes`` cuando vuelve la
  conexión, conservando su ``fecha_hora`` real.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def _conn():
    # Import diferido: database.py arrastra pandas y solo se necesita aquí.
    from MACRO.database import get_db_connection

    return get_db_connection()


def ensure_tablas_auth() -> None:
    """Crea las tablas de caché/cola si no existen. Idempotente."""
    conn = _conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_cache (
                usuario_red TEXT PRIMARY KEY,
                usuario_id  INTEGER NOT NULL,
                estado      TEXT NOT NULL,
                fecha_ok    TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS logueos_pendientes (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id        INTEGER NOT NULL,
                resultado         TEXT NOT NULL,
                ip_maquina        TEXT,
                fecha_hora_local  TEXT NOT NULL,
                version           TEXT
            )
            """
        )
        # Migración para BD ya creadas sin la columna 'version' (SQLite lanza
        # OperationalError si ya existe; es idempotente y esperado).
        try:
            conn.execute("ALTER TABLE logueos_pendientes ADD COLUMN version TEXT")
        except Exception:  # noqa: BLE001 — la columna ya existe
            pass
        conn.commit()
    finally:
        conn.close()


def upsert_aprobado(usuario_red: str, usuario_id: int) -> None:
    """Registra/actualiza al usuario como aprobado en la caché local."""
    conn = _conn()
    try:
        conn.execute(
            """
            INSERT INTO auth_cache (usuario_red, usuario_id, estado, fecha_ok)
            VALUES (?, ?, 'aprobado', ?)
            ON CONFLICT(usuario_red) DO UPDATE SET
                usuario_id = excluded.usuario_id,
                estado     = 'aprobado',
                fecha_ok   = excluded.fecha_ok
            """,
            (usuario_red, usuario_id, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()


def get(usuario_red: str) -> dict[str, Any] | None:
    """Devuelve ``{usuario_id, estado, fecha_ok}`` cacheado o ``None``."""
    conn = _conn()
    try:
        cur = conn.execute(
            "SELECT usuario_id, estado, fecha_ok FROM auth_cache WHERE usuario_red = ?",
            (usuario_red,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {"usuario_id": row[0], "estado": row[1], "fecha_ok": row[2]}


def encolar_logueo(
    usuario_id: int,
    resultado: str,
    ip_maquina: str | None,
    fecha_hora_local: datetime | None = None,
    version: str | None = None,
) -> None:
    """Encola un logueo que no se pudo enviar a Oracle."""
    fecha = (fecha_hora_local or datetime.now()).isoformat(timespec="seconds")
    conn = _conn()
    try:
        conn.execute(
            """
            INSERT INTO logueos_pendientes
                (usuario_id, resultado, ip_maquina, fecha_hora_local, version)
            VALUES (?, ?, ?, ?, ?)
            """,
            (usuario_id, resultado, ip_maquina, fecha, version),
        )
        conn.commit()
    finally:
        conn.close()


def listar_pendientes() -> list[dict[str, Any]]:
    """Lista los logueos encolados, del más antiguo al más reciente."""
    conn = _conn()
    try:
        cur = conn.execute(
            """
            SELECT id, usuario_id, resultado, ip_maquina, fecha_hora_local, version
            FROM logueos_pendientes ORDER BY id
            """
        )
        filas = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "id": f[0],
            "usuario_id": f[1],
            "resultado": f[2],
            "ip_maquina": f[3],
            "fecha_hora_local": datetime.fromisoformat(f[4]),
            "version": f[5],
        }
        for f in filas
    ]


def borrar_pendiente(pendiente_id: int) -> None:
    """Elimina un logueo de la cola tras subirlo con éxito."""
    conn = _conn()
    try:
        conn.execute("DELETE FROM logueos_pendientes WHERE id = ?", (pendiente_id,))
        conn.commit()
    finally:
        conn.close()
