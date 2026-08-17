from unittest.mock import patch

from fastapi.testclient import TestClient

from MACRO.app.server import create_app


class FakeJobs:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run(self, tarea, *, kind: str, num_doc: str | None = None) -> str:
        self.calls.append(kind)
        return "job-xyz"


def test_listar_descargas() -> None:
    fila = {
        "id": 1,
        "num_doc": "D1",
        "ruc": "10",
        "tipo_servicio": "PORTAL",
        "tipo_descarga": "RI",
        "parametro": "RI-1",
        "estado": "PENDIENTE",
        "reintentos": 0,
        "error_log": "",
    }
    with patch("MACRO.database.obtener_descargas_bd", return_value=[fila]):
        client = TestClient(create_app())
        resp = client.get("/api/mantenimiento/descargas")
    assert resp.status_code == 200
    assert resp.json()["descargas"][0]["num_doc"] == "D1"


def test_eliminar_descargas() -> None:
    with patch("MACRO.database.eliminar_descargas_bd", return_value=2) as el:
        client = TestClient(create_app())
        resp = client.post("/api/mantenimiento/descargas/eliminar", json={"ids": [1, 2]})
    assert resp.status_code == 200
    assert resp.json() == {"eliminadas": 2}
    el.assert_called_once_with([1, 2])


def test_ejecutar_descargas_lanza_job() -> None:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post("/api/mantenimiento/descargas/ejecutar", json={"ids": [3]})
    assert resp.status_code == 200
    assert resp.json() == {"job_id": "job-xyz"}
    assert fake.calls == ["descarga_seleccionada"]


def test_borrar_bd() -> None:
    with patch("MACRO.database.limpiar_tablas_asignacion") as limp:
        client = TestClient(create_app())
        resp = client.post("/api/mantenimiento/borrar-bd")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    limp.assert_called_once()


def test_borrar_descargas() -> None:
    with patch("MACRO.database.limpiar_tabla_desc_bd") as limp:
        client = TestClient(create_app())
        resp = client.post("/api/mantenimiento/borrar-descargas")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    limp.assert_called_once()


def test_borrar_caso_endpoint() -> None:
    with patch(
        "MACRO.flujos.flujo_validar_archivo.borrar_caso_completo",
        return_value={"eliminadas": {"tabla_asign": 1}, "carpeta_borrada": True,
                      "carpeta": "C:/x"},
    ) as bcc:
        client = TestClient(create_app())
        resp = client.post("/api/mantenimiento/borrar-caso",
                           json={"num_doc": "D1", "borrar_carpeta": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["eliminadas"]["tabla_asign"] == 1
    assert body["carpeta_borrada"] is True
    bcc.assert_called_once_with("D1", True)
