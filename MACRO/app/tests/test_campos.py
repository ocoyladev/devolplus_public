from unittest.mock import patch

from fastapi.testclient import TestClient

from MACRO.app.server import create_app


def test_patch_campo_resultado_llama_db() -> None:
    with patch("MACRO.database.actualizar_dato_celda", return_value=True) as m:
        client = TestClient(create_app())
        resp = client.patch(
            "/api/campos/123-ABC",
            json={"campo": "resultado", "valor": "PROCEDENTE"},
        )
    assert resp.status_code == 200
    assert resp.json() == {
        "ok": True,
        "num_doc": "123-ABC",
        "campo": "resultado",
        "valor": "PROCEDENTE",
    }
    m.assert_called_once_with("tabla_asign", "resultado", "PROCEDENTE", "123-ABC")


def test_patch_campo_ri_mapea_a_num_ri() -> None:
    with patch("MACRO.database.actualizar_dato_celda", return_value=True) as m:
        client = TestClient(create_app())
        resp = client.patch("/api/campos/999", json={"campo": "ri", "valor": "RI-1"})
    assert resp.status_code == 200
    m.assert_called_once_with("tabla_asign", "num_ri", "RI-1", "999")


def test_patch_campo_invalido_rechazado() -> None:
    client = TestClient(create_app())
    resp = client.patch("/api/campos/123", json={"campo": "inexistente", "valor": "x"})
    assert resp.status_code == 422


def test_patch_campo_falla_db_devuelve_500() -> None:
    with patch("MACRO.database.actualizar_dato_celda", return_value=False):
        client = TestClient(create_app())
        resp = client.patch("/api/campos/123", json={"campo": "carta", "valor": "C-1"})
    assert resp.status_code == 500
