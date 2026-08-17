from fastapi.testclient import TestClient

from MACRO.app.server import create_app


def test_progreso_de_job_se_difunde_por_websocket() -> None:
    app = create_app()
    with TestClient(app) as client:  # el lifespan captura el loop
        with client.websocket_connect("/ws") as ws:
            jobs = app.state.jobs

            def tarea(progreso):
                progreso("hola")

            jobs.run(tarea, kind="test", num_doc="1")

            msg1 = ws.receive_json()
            msg2 = ws.receive_json()

    assert msg1["type"] == "progress"
    assert msg1["msg"] == "hola"
    assert msg1["num_doc"] == "1"
    assert msg2["type"] == "job_done"
    assert msg2["ok"] is True
    assert msg1["job_id"] == msg2["job_id"]
