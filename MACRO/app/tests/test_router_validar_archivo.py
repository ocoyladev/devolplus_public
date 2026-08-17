from unittest.mock import patch

from fastapi.testclient import TestClient

from MACRO.app.server import create_app


def test_validar_archivo_endpoint_ok():
    fake = {"casos": [{
        "num_doc": "D1", "num_dev": "", "num_ruc": "", "nombre": "", "of_devolucion": "",
        "tipo_exp": "FISICO", "is_of_multiple": False, "carpeta_existe": True,
        "paso_pptt": True,
        "insumo_final": {"completo": True, "faltantes": [], "puede_foliar": False},
        "exp_echasqui": {"registrado": True, "valor": "", "autoregistrado": False},
        "carga_1649": {"aplica": False, "local": {"reportes": False, "cedula": False},
                       "remoto": "na", "remoto_reportes": False, "remoto_cedula": False},
        "indispensables": {"raiz": [], "subcarpetas": {}},
        "alertas": [], "nivel": "ok", "error": "",
    }]}
    app = create_app()
    with patch("MACRO.flujos.flujo_validar_archivo.validar_casos", return_value=fake):
        client = TestClient(app)
        r = client.post("/api/procesos/validar-archivo", json={"num_docs": ["D1"]})
    assert r.status_code == 200
    assert r.json()["casos"][0]["num_doc"] == "D1"


def test_abrir_carpeta_endpoint(monkeypatch):
    import MACRO.flujos.flujo_validar_archivo as fva

    monkeypatch.setattr(fva, "_fila_de", lambda nd: None)  # no abre nada real

    app = create_app()
    with TestClient(app) as client:
        resp = client.post(
            "/api/procesos/validar-archivo/abrir-carpeta", json={"num_doc": "D1"}
        )
    assert resp.status_code == 204
