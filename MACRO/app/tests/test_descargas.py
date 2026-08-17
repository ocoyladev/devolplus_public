from fastapi.testclient import TestClient

from MACRO.app.server import create_app


class FakeJobs:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def run(self, tarea, *, kind: str, num_doc: str | None = None) -> str:
        self.calls.append((kind, num_doc))
        return "job-xyz"


def test_post_echasqui_lanza_job_con_kind_y_num_doc() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post(
        "/api/descargas/echasqui",
        json={"row": {"num_doc": "D1"}, "expedientes": ["E1", "E2"]},
    )
    assert resp.status_code == 200
    assert resp.json() == {"job_id": "job-xyz"}
    assert fake.calls == [("descarga_echasqui", "D1")]


def test_post_echasqui_valida_body() -> None:
    app = create_app()
    app.state.jobs = FakeJobs()
    client = TestClient(app)
    resp = client.post("/api/descargas/echasqui", json={"row": {"num_doc": "D1"}})
    assert resp.status_code == 422  # falta 'expedientes'


def test_post_reintentar_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post("/api/descargas/reintentar")
    assert resp.status_code == 200
    assert fake.calls == [("reintentar_descargas", None)]


def test_post_numeracion_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post(
        "/api/descargas/numeracion",
        json={"filas": [{"num_doc": "D1", "carta": "78954-2026"}]},
    )
    assert resp.status_code == 200
    assert resp.json() == {"job_id": "job-xyz"}
    assert fake.calls == [("numeracion_cartas", None)]


def test_post_ri_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post(
        "/api/descargas/ri",
        json={"row": {"num_doc": "D9"}, "ri_valor": "RI-1"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"job_id": "job-xyz"}
    assert fake.calls == [("descarga_ri", "D9")]


def test_post_cartas_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post(
        "/api/descargas/cartas",
        json={"row": {"num_doc": "D7"}, "cartas_valor": "1234-2024"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"job_id": "job-xyz"}
    assert fake.calls == [("descarga_cartas", "D7")]


def test_post_exp_electronico_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post(
        "/api/descargas/exp-electronico", json={"row": {"num_doc": "D3"}}
    )
    assert resp.status_code == 200
    assert resp.json() == {"job_id": "job-xyz"}
    assert fake.calls == [("descarga_exp_electronico", "D3")]


def test_post_3uit_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post(
        "/api/descargas/3uit", json={"row": {"num_doc": "D5"}, "num_formulario": "777"}
    )
    assert resp.status_code == 200
    assert fake.calls == [("descarga_3uit", "D5")]


def test_post_ejercicios_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post(
        "/api/descargas/ejercicios", json={"row": {"num_doc": "D6"}, "count": 2}
    )
    assert resp.status_code == 200
    assert fake.calls == [("descarga_ejercicios", "D6")]


def test_post_planeamiento_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post(
        "/api/descargas/planeamiento",
        json={"row": {"num_doc": "D8"}, "ruc": "10316187447"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"job_id": "job-xyz"}
    assert fake.calls == [("descarga_planeamiento", "D8")]


def test_post_planeamiento_valida_body() -> None:
    app = create_app()
    app.state.jobs = FakeJobs()
    client = TestClient(app)
    resp = client.post("/api/descargas/planeamiento", json={"row": {"num_doc": "D8"}})
    assert resp.status_code == 422  # falta 'ruc'


def _client_masivo():
    app = create_app()
    app.state.jobs = FakeJobs()
    return TestClient(app)


def test_ri_masivo_lanza_job() -> None:
    r = _client_masivo().post("/api/descargas/ri-masivo",
                              json={"filas": [{"num_doc": "1"}], "archivo": True})
    assert r.status_code == 200 and r.json() == {"job_id": "job-xyz"}


def test_cartas_masivo_lanza_job() -> None:
    r = _client_masivo().post("/api/descargas/cartas-masivo",
                              json={"filas": [{"num_doc": "1"}], "archivo": False})
    assert r.status_code == 200 and r.json() == {"job_id": "job-xyz"}


def test_ri_single_acepta_archivo() -> None:
    r = _client_masivo().post("/api/descargas/ri",
                              json={"row": {"num_doc": "1"}, "archivo": True})
    assert r.status_code == 200


def test_post_rsirat_preflight_devuelve_la_verificacion_sin_job() -> None:
    """El preflight es síncrono: responde el detalle por caso y NO crea un job."""
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)

    resp = client.post(
        "/api/descargas/rsirat-preflight",
        json={"tipo": "ref", "filas": []},
    )

    assert resp.status_code == 200
    assert resp.json() == {"tipo": "ref", "total": 0, "pendientes": 0, "casos": []}
    assert fake.calls == []


def test_post_rsirat_preflight_rechaza_tipo_desconocido() -> None:
    app = create_app()
    app.state.jobs = FakeJobs()
    client = TestClient(app)
    resp = client.post(
        "/api/descargas/rsirat-preflight",
        json={"tipo": "otro", "filas": []},
    )
    assert resp.status_code == 422
