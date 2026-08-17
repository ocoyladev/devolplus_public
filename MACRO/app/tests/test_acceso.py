"""Tests del control de acceso (Oracle mockeado, caché en SQLite temporal)."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from MACRO.app.server import create_app
from MACRO.auth import auth_service, cache_local


# --- Dobles de prueba para la conexión Oracle ------------------------------

class FakeCursor:
    def __init__(self, conn: "FakeConn") -> None:
        self._conn = conn
        self._fetchone: object = None
        self.rowcount = 1

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def execute(self, sql: str, params: list | None = None) -> None:
        sql_norm = " ".join(sql.split())
        self._conn.ejecutadas.append((sql_norm, params))
        if "SELECT id, estado FROM usuarios" in sql_norm:
            self._fetchone = self._conn.usuario_row

    def fetchone(self) -> object:
        return self._fetchone


class FakeConn:
    def __init__(self, usuario_row: tuple | None) -> None:
        self.usuario_row = usuario_row
        self.ejecutadas: list[tuple[str, list | None]] = []
        self.commits = 0
        self.closed = False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        self.closed = True


def _fake_get_connection(usuario_row: tuple | None):
    def _factory() -> FakeConn:
        return FakeConn(usuario_row)

    return _factory


@pytest.fixture(autouse=True)
def _cache_temporal(tmp_path, monkeypatch):
    """Redirige la caché local a un SQLite temporal por test.

    Fuerza además ``AUTH_MODE = "oracle"``: los tests de este bloque ejercitan
    la rama que consulta la base corporativa, que el modo demo cortocircuita.
    El modo demo se prueba aparte, en :func:`test_modo_demo_permite_sin_bd`.
    """
    db = tmp_path / "cache.db"

    def _conn() -> sqlite3.Connection:
        return sqlite3.connect(db)

    monkeypatch.setattr(cache_local, "_conn", _conn)
    monkeypatch.setattr(auth_service, "AUTH_MODE", "oracle")
    cache_local.ensure_tablas_auth()
    yield


# --- modo demo --------------------------------------------------------------

def test_modo_demo_permite_sin_bd(monkeypatch):
    """Con AUTH_MODE=demo el acceso se concede sin tocar la base corporativa."""
    monkeypatch.setattr(auth_service, "AUTH_MODE", "demo")

    def _explota():
        raise AssertionError("el modo demo no debe abrir conexión a la BD")

    monkeypatch.setattr(auth_service, "get_connection", _explota)

    r = auth_service.verificar_acceso("jdoe")

    assert r["estado"] == "permitido"
    assert r["usuario_red"] == "jdoe"
    assert r["usuario_id"] == auth_service.DEMO_USUARIO_ID


def test_modo_demo_solicitud_no_persiste(monkeypatch):
    """En demo la solicitud de acceso se acusa sin escribir en ninguna tabla."""
    monkeypatch.setattr(auth_service, "AUTH_MODE", "demo")

    r = auth_service.solicitar_acceso("Juan Doe", "jdoe", "jdoe@example.org")

    assert r["ok"] is True
    assert "demostración" in r["mensaje"].lower()


# --- verificar_acceso: caminos online --------------------------------------

def _sql_ejecutadas(conns: list[FakeConn]) -> list[str]:
    return [sql for c in conns for sql, _ in c.ejecutadas]


def test_usuario_aprobado_permite_y_audita_exitoso() -> None:
    creadas: list[FakeConn] = []

    def factory() -> FakeConn:
        c = FakeConn(usuario_row=(7, "aprobado"))
        creadas.append(c)
        return c

    with patch.object(auth_service, "get_connection", factory):
        r = auth_service.verificar_acceso("jdoe")

    assert r["estado"] == "permitido"
    assert r["usuario_id"] == 7
    assert any("INSERT INTO registro_logueos" in s for s in _sql_ejecutadas(creadas))
    assert any("exitoso" == p[1] for c in creadas for s, p in c.ejecutadas
               if "registro_logueos" in s and p)
    # La aprobación queda cacheada localmente.
    assert cache_local.get("jdoe") == {
        "usuario_id": 7,
        "estado": "aprobado",
        "fecha_ok": cache_local.get("jdoe")["fecha_ok"],
    }


@pytest.mark.parametrize(
    "estado,resultado",
    [
        ("pendiente", "denegado_pendiente"),
        ("rechazado", "denegado_rechazado"),
        ("inactivo", "denegado_inactivo"),
    ],
)
def test_usuario_no_aprobado_deniega_y_audita(estado: str, resultado: str) -> None:
    creadas: list[FakeConn] = []

    def factory() -> FakeConn:
        c = FakeConn(usuario_row=(3, estado))
        creadas.append(c)
        return c

    with patch.object(auth_service, "get_connection", factory):
        r = auth_service.verificar_acceso("jdoe")

    assert r["estado"] == estado
    assert any(
        p and resultado in p for c in creadas for s, p in c.ejecutadas
        if "registro_logueos" in s
    )
    assert cache_local.get("jdoe") is None  # no se cachea un no-aprobado


def test_usuario_inexistente_pide_registro() -> None:
    with patch.object(auth_service, "get_connection", _fake_get_connection(None)):
        r = auth_service.verificar_acceso("nuevo")
    assert r["estado"] == "no_registrado"


# --- verificar_acceso: caminos offline -------------------------------------

def test_offline_con_cache_aprobado_permite_y_encola() -> None:
    cache_local.upsert_aprobado("jdoe", 7)

    def boom() -> FakeConn:
        raise RuntimeError("Oracle caído")

    with patch.object(auth_service, "get_connection", boom):
        r = auth_service.verificar_acceso("jdoe")

    assert r["estado"] == "permitido"
    pendientes = cache_local.listar_pendientes()
    assert len(pendientes) == 1
    assert pendientes[0]["resultado"] == "exitoso"
    assert pendientes[0]["usuario_id"] == 7


def test_offline_sin_cache_deniega() -> None:
    def boom() -> FakeConn:
        raise RuntimeError("Oracle caído")

    with patch.object(auth_service, "get_connection", boom):
        r = auth_service.verificar_acceso("desconocido")

    assert r["estado"] == "sin_conexion"
    assert cache_local.listar_pendientes() == []


# --- flush_pendientes -------------------------------------------------------

def test_flush_sube_pendientes_con_fecha_real_y_vacia_cola() -> None:
    momento = datetime(2026, 7, 8, 9, 30, 0)
    cache_local.encolar_logueo(7, "exitoso", "10.0.0.1", momento)
    conn = FakeConn(usuario_row=None)

    enviados = auth_service.flush_pendientes(conn)

    assert enviados == 1
    assert cache_local.listar_pendientes() == []
    inserts = [p for s, p in conn.ejecutadas if "registro_logueos" in s]
    assert inserts and momento in inserts[0]  # se insertó el timestamp real


# --- Router /api/acceso -----------------------------------------------------

def test_get_acceso_devuelve_estado() -> None:
    with patch(
        "MACRO.auth.auth_service.verificar_acceso",
        return_value={
            "estado": "pendiente",
            "usuario_red": "jdoe",
            "usuario_id": 1,
            "mensaje": "Su solicitud está pendiente.",
        },
    ):
        client = TestClient(create_app())
        resp = client.get("/api/acceso")
    assert resp.status_code == 200
    assert resp.json()["estado"] == "pendiente"
    assert resp.json()["usuario_red"] == "jdoe"


def test_post_solicitud_registra() -> None:
    with patch(
        "MACRO.auth.auth_service.solicitar_acceso",
        return_value={"ok": True, "mensaje": "Solicitud registrada."},
    ), patch("MACRO.auth.auth_service.obtener_usuario_red", return_value="jdoe"):
        client = TestClient(create_app())
        resp = client.post(
            "/api/acceso/solicitud",
            json={"nombre_completo": "Juan Doe", "email": "j@x.com"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "mensaje": "Solicitud registrada."}
