from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

from MACRO.app.server import create_app

PATH = "MACRO.flujos.flujo_asignacion_excel.obtener_dataframe_actual"


def test_get_tabla_serializa_dataframe() -> None:
    df = pd.DataFrame(
        [
            {"num_doc": "1", "nombre": "A", "resultado": None},
            {"num_doc": "2", "nombre": "B", "resultado": "OK"},
        ]
    )
    with patch(PATH, return_value=df):
        client = TestClient(create_app())
        resp = client.get("/api/datos/tabla")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["columns"] == ["num_doc", "nombre", "resultado"]
    assert data["rows"][0]["num_doc"] == "1"
    assert data["rows"][0]["resultado"] is None
    assert data["rows"][1]["resultado"] == "OK"


def test_get_tabla_formatea_columnas_datetime_a_ddmmyyyy() -> None:
    df = pd.DataFrame(
        {"num_doc": ["1"], "vcto": pd.to_datetime(["2026-05-19"])}
    )
    with patch(PATH, return_value=df):
        client = TestClient(create_app())
        resp = client.get("/api/datos/tabla")
    assert resp.status_code == 200
    assert resp.json()["rows"][0]["vcto"] == "19/05/2026"


def test_fec_ri_es_columna_fecha_reconocida() -> None:
    # fec_ri debe tratarse como fecha para que la grilla la muestre DD/MM/YYYY
    # (antes se quedaba como el Timestamp crudo "2026-05-01 00:00:00").
    from MACRO.funciones.funciones_generales import COLUMNAS_FECHA_DB, parsear_columnas_fecha

    assert "fec_ri" in COLUMNAS_FECHA_DB
    df = pd.DataFrame({"num_doc": ["1"], "fec_ri": ["2026-05-01 00:00:00"]})
    parsear_columnas_fecha(df)
    with patch(PATH, return_value=df):
        client = TestClient(create_app())
        resp = client.get("/api/datos/tabla")
    assert resp.json()["rows"][0]["fec_ri"] == "01/05/2026"


def test_planeamiento_estado_devuelve_permitido() -> None:
    with patch(
        "MACRO.funciones.funciones_generales.planeamiento_permitido",
        return_value=False,
    ):
        client = TestClient(create_app())
        resp = client.get("/api/datos/planeamiento-estado")
    assert resp.status_code == 200
    assert resp.json() == {"permitido": False}


def test_get_archivo_serializa_dataframe() -> None:
    df = pd.DataFrame([{"num_doc": "1", "nombre": "A"}])
    with patch(
        "MACRO.flujos.flujo_asignacion_excel.obtener_dataframe_archivo",
        return_value=df,
    ):
        client = TestClient(create_app())
        resp = client.get("/api/datos/archivo")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["rows"][0]["num_doc"] == "1"


def test_get_tabla_vacia_devuelve_estructura_vacia() -> None:
    with patch(PATH, return_value=None):
        client = TestClient(create_app())
        resp = client.get("/api/datos/tabla")
    assert resp.status_code == 200
    assert resp.json() == {"columns": [], "rows": [], "total": 0}


class _FakeJobs:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run(self, tarea, *, kind: str, num_doc=None) -> str:
        self.calls.append(kind)
        return "job-xyz"


def test_post_cargar_lanza_job() -> None:
    app = create_app()
    fake = _FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post("/api/datos/cargar", json={"num_docs": ["1", "2"]})
    assert resp.status_code == 200
    assert resp.json() == {"job_id": "job-xyz"}
    assert fake.calls == ["cargar_datos"]


def test_post_cargar_archivo_lanza_job_por_tipo() -> None:
    app = create_app()
    fake = _FakeJobs()
    app.state.jobs = fake
    client = TestClient(app)
    resp = client.post(
        "/api/datos/cargar-archivo",
        data={"tipo": "sistema_legacy"},
        files={"file": ("reporte.xlsx", b"datos", "application/vnd.ms-excel")},
    )
    assert resp.status_code == 200
    assert resp.json() == {"job_id": "job-xyz"}
    assert fake.calls == ["cargar_sistema_legacy"]
