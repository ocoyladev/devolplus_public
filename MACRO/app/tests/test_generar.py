from unittest.mock import patch

from fastapi.testclient import TestClient

from MACRO.app.server import create_app


class FakeJobs:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run(self, tarea, *, kind: str, num_doc=None) -> str:
        self.calls.append(kind)
        return "job-xyz"


def test_listar_modelos() -> None:
    with patch(
        "MACRO.flujos.flujo_documentos.listar_modelos", return_value=["a.docx", "b.docx"]
    ):
        client = TestClient(create_app())
        resp = client.get("/api/generar/modelos/carta")
    assert resp.status_code == 200
    assert resp.json() == {"modelos": ["a.docx", "b.docx"]}


def test_generar_carta_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post(
        "/api/generar/carta",
        json={"row": {"num_doc": "D1"}, "modelos": ["m.docx"], "plazo": 5},
    )
    assert resp.status_code == 200
    assert fake.calls == ["generar_carta"]


def test_generar_ri_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post(
        "/api/generar/ri", json={"row": {"num_doc": "D2"}, "modelo": "ri.docx"}
    )
    assert resp.status_code == 200
    assert fake.calls == ["generar_ri"]
