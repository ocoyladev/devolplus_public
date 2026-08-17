from fastapi.testclient import TestClient

from MACRO.app.server import create_app


class FakeJobs:
    def run(self, tarea, *, kind="task", num_doc=None):
        return "job-xyz"


def _client():
    app = create_app()
    app.state.jobs = FakeJobs()
    return TestClient(app)


def test_post_archivar_echasqui_lanza_job():
    r = _client().post("/api/procesos/archivar-echasqui", json={"num_docs": ["111"]})
    assert r.status_code == 200 and r.json()["job_id"] == "job-xyz"


def test_listar_archivar_echasqui(monkeypatch):
    monkeypatch.setattr(
        "MACRO.database.listar_archivar_echasqui",
        lambda: [{"id": 1, "num_doc": "111", "ruc": "10", "num_ri": "R",
                  "aduana": "000", "urd": "URD999", "anio": "2026",
                  "nroexpedi": "629310", "denom": "d", "estado": "pendiente",
                  "mensaje": "", "fecha_registro": "x"}],
    )
    r = _client().get("/api/mantenimiento/archivar-echasqui")
    assert r.status_code == 200 and len(r.json()["pendientes"]) == 1


def test_eliminar_archivar_echasqui(monkeypatch):
    monkeypatch.setattr("MACRO.database.eliminar_archivar_echasqui", lambda ids: len(ids))
    r = _client().post("/api/mantenimiento/archivar-echasqui/eliminar", json={"ids": [1, 2]})
    assert r.status_code == 200 and r.json()["eliminadas"] == 2


def test_ejecutar_archivar_echasqui_lanza_job():
    r = _client().post("/api/mantenimiento/archivar-echasqui/ejecutar", json={"ids": [1]})
    assert r.status_code == 200 and r.json()["job_id"] == "job-xyz"


def test_jobs_reenvia_detalle():
    from MACRO.app.jobs import JobManager
    eventos: list[dict] = []
    jm = JobManager(eventos.append)
    job_id = jm.run(lambda progreso: {"exito": True, "mensaje": "ok",
                                      "detalle": [{"num_doc": "1", "exp": "e",
                                                   "resultado": "archivado", "mensaje": "m"}]},
                    kind="archivar_echasqui")
    jm.join(job_id, timeout=5)
    done = [e for e in eventos if e["type"] == "job_done"][-1]
    assert done["detalle"][0]["resultado"] == "archivado"
