"""Tests del backend admin (admin_service mockeado)."""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from admin_accesos.backend.server import create_app


def test_listar_solicitudes_filtra_por_estado() -> None:
    with patch(
        "MACRO.auth.admin_service.listar_solicitudes",
        return_value=[{"id": 1, "usuario_red": "jdoe", "estado": "pendiente"}],
    ) as m:
        client = TestClient(create_app())
        resp = client.get("/api/solicitudes", params={"estado": "pendiente"})
    assert resp.status_code == 200
    assert resp.json()[0]["usuario_red"] == "jdoe"
    m.assert_called_once_with("pendiente")


def test_decidir_actualiza_estado_con_admin_actual() -> None:
    with patch(
        "MACRO.auth.admin_service.actualizar_estado",
        return_value={"ok": True, "mensaje": "Usuario actualizado a 'aprobado'."},
    ) as m, patch(
        "MACRO.auth.auth_service.obtener_usuario_red", return_value="jdoe"
    ):
        client = TestClient(create_app())
        resp = client.patch(
            "/api/solicitudes/5", json={"estado": "aprobado", "observaciones": "ok"}
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    m.assert_called_once_with(
        usuario_id=5, nuevo_estado="aprobado", admin_actual="jdoe", observaciones="ok"
    )


def test_decidir_estado_invalido_es_422() -> None:
    client = TestClient(create_app())
    resp = client.patch("/api/solicitudes/5", json={"estado": "borrar"})
    assert resp.status_code == 422  # Literal de Pydantic rechaza el valor


def test_logueos_pasa_filtros() -> None:
    with patch(
        "MACRO.auth.admin_service.historial_logueos",
        return_value=[{"usuario_red": "jdoe", "resultado": "exitoso"}],
    ) as m:
        client = TestClient(create_app())
        resp = client.get("/api/logueos", params={"usuario_red": "jdoe", "limite": 10})
    assert resp.status_code == 200
    m.assert_called_once_with("jdoe", 10)


def test_error_de_bd_devuelve_503() -> None:
    with patch(
        "MACRO.auth.admin_service.listar_solicitudes",
        side_effect=RuntimeError("Oracle caído"),
    ):
        client = TestClient(create_app())
        resp = client.get("/api/solicitudes")
    assert resp.status_code == 503


# --- Historial de logueos en hora de Perú (UTC-5) ----------------------------
def test_iso_hora_peru_convierte_utc_naive() -> None:
    from datetime import datetime, timedelta, timezone

    from MACRO.auth import admin_service

    # Lo que devuelve la columna TIMESTAMP: naive, en UTC.
    assert (admin_service._iso_hora_peru(datetime(2026, 8, 10, 14, 30, 5))
            == "2026-08-10T09:30:05-05:00")
    # Cruce de día: 02:00 UTC es el día anterior en Perú.
    assert (admin_service._iso_hora_peru(datetime(2026, 8, 10, 2, 0, 0))
            == "2026-08-09T21:00:00-05:00")
    # Si ya viniera con zona, se respeta el instante.
    con_zona = datetime(2026, 8, 10, 14, 30, 5, tzinfo=timezone(timedelta(hours=0)))
    assert admin_service._iso_hora_peru(con_zona) == "2026-08-10T09:30:05-05:00"
    # Valores que no son fecha pasan intactos.
    assert admin_service._iso_hora_peru(None) is None
    assert admin_service._iso_hora_peru("x") == "x"


def test_historial_logueos_devuelve_fecha_en_hora_peru() -> None:
    from datetime import datetime
    from unittest.mock import MagicMock

    from MACRO.auth import admin_service

    cur = MagicMock()
    cur.description = [("USUARIO_RED",), ("FECHA_HORA",), ("RESULTADO",),
                       ("IP_MAQUINA",), ("VERSION",)]
    cur.fetchall.return_value = [
        ("jdoe", datetime(2026, 8, 10, 14, 30, 5), "exitoso", "10.0.0.1", "1.1.7"),
    ]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur

    with patch("MACRO.auth.admin_service.get_connection", return_value=conn):
        filas = admin_service.historial_logueos()

    assert filas[0]["fecha_hora"] == "2026-08-10T09:30:05-05:00"
    assert filas[0]["usuario_red"] == "jdoe"
