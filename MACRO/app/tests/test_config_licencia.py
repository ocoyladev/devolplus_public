from unittest.mock import patch

from fastapi.testclient import TestClient

from MACRO.app.server import create_app


def test_get_rutas_lee_config() -> None:
    with patch("MACRO.database.obtener_config", side_effect=lambda k, d=None: f"val-{k}"):
        client = TestClient(create_app())
        resp = client.get("/api/config/rutas")
    assert resp.status_code == 200
    assert resp.json()["PATH_DESCARGAS"] == "val-PATH_DESCARGAS"


def test_unidad_organica_default_7ec400_cuando_no_guardada() -> None:
    # obtener_config devuelve el default recibido cuando no hay valor guardado.
    with patch("MACRO.database.obtener_config", side_effect=lambda k, d=None: d):
        client = TestClient(create_app())
        resp = client.get("/api/config/rutas")
    assert resp.json()["UNIDAD_ORGANICA_FOLIO"] == "7EC400"


def test_put_rutas_guarda_solo_provistas() -> None:
    with patch("MACRO.database.guardar_config") as g, patch(
        "MACRO.database.obtener_config", side_effect=lambda k, d=None: None
    ):
        client = TestClient(create_app())
        resp = client.put("/api/config/rutas", json={"PATH_RI": "D:/RI"})
    assert resp.status_code == 200
    g.assert_called_once_with("PATH_RI", "D:/RI")


def test_get_credenciales_no_expone_password() -> None:
    with patch(
        "MACRO.database.obtener_credenciales",
        return_value={"usuario": "jdoe", "password": "secreto"},
    ):
        client = TestClient(create_app())
        resp = client.get("/api/config/credenciales/Portal")
    assert resp.status_code == 200
    assert resp.json() == {"sistema": "Portal", "usuario": "jdoe"}
    assert "password" not in resp.json()


def test_put_credenciales_portal_se_guarda_en_mayusculas() -> None:
    with patch("MACRO.database.guardar_credenciales") as g:
        client = TestClient(create_app())
        resp = client.put(
            "/api/config/credenciales",
            json={"sistema": "Portal", "usuario": "jdoe", "password": "p"},
        )
    assert resp.status_code == 200
    assert resp.json()["usuario"] == "JDOE"
    g.assert_called_once_with("Portal", "JDOE", "p")


def test_put_credenciales_otros_sistemas_respetan_caso() -> None:
    with patch("MACRO.database.guardar_credenciales") as g:
        client = TestClient(create_app())
        resp = client.put(
            "/api/config/credenciales",
            json={"sistema": "Workflow", "usuario": "User1", "password": "p"},
        )
    assert resp.json()["usuario"] == "User1"
    g.assert_called_once_with("Workflow", "User1", "p")


def test_feriados_add_convierte_ddmmyyyy_a_ymd() -> None:
    with patch("MACRO.database.agregar_feriado") as add, patch(
        "MACRO.database.obtener_feriados", return_value=["2026-12-25"]
    ):
        client = TestClient(create_app())
        resp = client.post("/api/config/feriados", json={"fecha": "25/12/2026"})
    assert resp.status_code == 200
    add.assert_called_once_with("2026-12-25")
    assert resp.json()["feriados"] == ["25/12/2026"]


def test_feriados_fecha_invalida_400() -> None:
    client = TestClient(create_app())
    resp = client.post("/api/config/feriados", json={"fecha": "no-fecha"})
    assert resp.status_code == 400
