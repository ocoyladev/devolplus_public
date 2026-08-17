from unittest.mock import patch

from fastapi.testclient import TestClient

from MACRO.app.server import create_app


class FakeJobs:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def run(self, tarea, *, kind: str, num_doc: str | None = None) -> str:
        self.calls.append((kind, num_doc))
        return "job-xyz"


def test_mesa_ayuda_descarga_4ta_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post(
        "/api/mesa-ayuda/descarga", json={"tipo": "4ta", "row": {"num_doc": "D1"}}
    )
    assert resp.status_code == 200
    assert fake.calls == [("mesa_ayuda_4ta", "D1")]


def test_mesa_ayuda_modificar_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post(
        "/api/mesa-ayuda/modificar",
        json={"row": {"num_doc": "D2"}, "modalidad": "De Cheque a OPF"},
    )
    assert resp.status_code == 200
    assert fake.calls == [("mesa_ayuda_modificar", "D2")]


def test_empleadores_601_devuelve_lista() -> None:
    with patch(
        "MACRO.flujos.flujo_mesa_ayuda.extraer_empleadores_601",
        return_value=[("20", "ACME"), ("30", "BETA")],
    ):
        client = TestClient(create_app())
        resp = client.post(
            "/api/mesa-ayuda/empleadores-601",
            json={"row": {"per_doc": "202312", "ruc": "20", "num_doc": "1"}},
        )
    assert resp.status_code == 200
    assert resp.json() == {
        "empleadores": [
            {"ruc": "20", "nombre": "ACME"},
            {"ruc": "30", "nombre": "BETA"},
        ]
    }


def test_empleadores_601_lista_vacia_si_falla() -> None:
    with patch(
        "MACRO.flujos.flujo_mesa_ayuda.extraer_empleadores_601",
        side_effect=RuntimeError("sin zip"),
    ):
        client = TestClient(create_app())
        resp = client.post(
            "/api/mesa-ayuda/empleadores-601",
            json={"row": {"per_doc": "202312", "ruc": "20"}},
        )
    assert resp.json() == {"empleadores": []}


def test_mesa_ayuda_descarga_tipo_invalido_rechazado() -> None:
    app = create_app()
    app.state.jobs = FakeJobs()
    client = TestClient(app)
    resp = client.post(
        "/api/mesa-ayuda/descarga", json={"tipo": "9na", "row": {"num_doc": "D1"}}
    )
    assert resp.status_code == 422


def test_mesa_ayuda_preview_4ta() -> None:
    client = TestClient(create_app())
    resp = client.post("/api/mesa-ayuda/preview", json={
        "tipo": "4ta",
        "row": {"of_devolucion": "OF1", "ruc": "10111111111",
                "nombre": "PEPE", "per_doc": "202412", "num_doc": "D1"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["tipo"] == "4ta"
    assert data["of"] == "OF1"
    assert data["contenido_txt"].startswith("10111111111|")
    assert data["titulo"] == "DESCARGA RENTAS DE 4TA_OF OF1"


def test_mesa_ayuda_preview_601_completo_usa_empleador() -> None:
    client = TestClient(create_app())
    resp = client.post("/api/mesa-ayuda/preview", json={
        "tipo": "601_completo",
        "row": {"of_devolucion": "OF9", "ruc": "10103903980",
                "nombre": "X", "per_doc": "202512", "num_doc": "D2"},
        "ruc_empleador": "20147907482", "nombre_empleador": "DIRESA",
    })
    assert resp.status_code == 200
    assert resp.json()["contenido_txt"] == "20147907482|202501|202512|"
