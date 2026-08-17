from unittest.mock import patch

from fastapi.testclient import TestClient

from MACRO.app.server import create_app

PATH = "MACRO.flujos.flujo_asignacion_excel.verificar_y_conectar_servicios"


def test_verificar_reporta_estado() -> None:
    with patch(PATH, return_value=(object(), None, False)):
        client = TestClient(create_app())
        resp = client.post("/api/servicios/verificar")
    assert resp.status_code == 200
    assert resp.json() == {"portal": True, "workflow": False}


def test_verificar_maneja_excepcion() -> None:
    with patch(PATH, side_effect=RuntimeError("red caída")):
        client = TestClient(create_app())
        resp = client.post("/api/servicios/verificar")
    assert resp.json() == {"portal": False, "workflow": False}
