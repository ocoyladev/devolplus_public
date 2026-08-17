from fastapi.testclient import TestClient

from MACRO.app.server import create_app


class FakeJobs:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run(self, tarea, *, kind: str, num_doc=None) -> str:
        self.calls.append(kind)
        return "job-xyz"


def test_sync_macros_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post("/api/sync/macros")
    assert resp.status_code == 200
    assert fake.calls == ["sync_macros"]


def test_sync_remota_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post("/api/sync/remota")
    assert resp.status_code == 200
    assert fake.calls == ["sync_remota"]
