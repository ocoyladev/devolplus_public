from unittest.mock import patch

from fastapi.testclient import TestClient

from MACRO.app.server import create_app

GCF = "MACRO.funciones.funciones_casos.get_case_folder"
OPEN = "MACRO.funciones.funciones_casos.abrir_en_sistema"


def test_abrir_carpeta_existente(tmp_path) -> None:
    with patch(GCF, return_value=str(tmp_path)), patch(OPEN) as op:
        client = TestClient(create_app())
        resp = client.post("/api/abrir/carpeta", json={"row": {"num_doc": "1"}})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "path": str(tmp_path)}
    op.assert_called_once_with(str(tmp_path))


def test_abrir_carpeta_inexistente_404() -> None:
    with patch(GCF, return_value="/no/existe/jamas"), patch(OPEN) as op:
        client = TestClient(create_app())
        resp = client.post("/api/abrir/carpeta", json={"row": {"num_doc": "1"}})
    assert resp.status_code == 404
    op.assert_not_called()


def test_abrir_macro_existente(tmp_path) -> None:
    (tmp_path / "MACRO.xlsx").write_text("x")
    with patch(GCF, return_value=str(tmp_path)), patch(OPEN) as op:
        client = TestClient(create_app())
        resp = client.post("/api/abrir/macro", json={"row": {"num_doc": "1"}})
    assert resp.status_code == 200
    op.assert_called_once()


def test_abrir_macro_tipo12_rechazado(tmp_path) -> None:
    with patch(GCF, return_value=str(tmp_path)), patch(OPEN) as op:
        client = TestClient(create_app())
        resp = client.post(
            "/api/abrir/macro", json={"row": {"num_doc": "1", "cod_sol": "12"}}
        )
    assert resp.status_code == 400
    op.assert_not_called()
