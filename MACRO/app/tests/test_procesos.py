import pandas as pd
from fastapi.testclient import TestClient

from MACRO.app.server import create_app


class FakeJobs:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run(self, tarea, *, kind: str, num_doc=None) -> str:
        self.calls.append(kind)
        return "job-xyz"


def _client_with_fake() -> tuple[TestClient, FakeJobs]:
    app = create_app()
    fake = FakeJobs()
    app.state.jobs = fake
    return TestClient(app), fake


def test_post_archivar_lanza_job() -> None:
    client, fake = _client_with_fake()
    resp = client.post("/api/procesos/archivar", json={"num_docs": ["1", "2"]})
    assert resp.status_code == 200
    assert resp.json() == {"job_id": "job-xyz"}
    assert fake.calls == ["archivar"]


def test_post_recuperar_lanza_job() -> None:
    client, fake = _client_with_fake()
    resp = client.post("/api/procesos/recuperar", json={"num_docs": ["1"]})
    assert resp.status_code == 200
    assert fake.calls == ["recuperar"]


def test_post_papeles_trabajo_lanza_job() -> None:
    client, fake = _client_with_fake()
    resp = client.post("/api/procesos/papeles-trabajo", json={"num_docs": ["1", "2"]})
    assert resp.status_code == 200
    assert fake.calls == ["papeles_trabajo"]


def test_post_carga_expedientes_lanza_job() -> None:
    client, fake = _client_with_fake()
    resp = client.post(
        "/api/procesos/carga-expedientes",
        json={"num_docs": ["1"], "ejecutar_firma_auto": True},
    )
    assert resp.status_code == 200
    assert fake.calls == ["carga_expedientes"]


def test_post_autorizar_lanza_job_con_decisiones(monkeypatch) -> None:
    import MACRO.flujos.flujo_autorizar as fa

    capturado = {}

    def fake_autorizar_casos(lineas, decisiones, decisiones_c64=None, callback_progreso=None):
        capturado["lineas"] = lineas
        capturado["decisiones"] = decisiones
        capturado["decisiones_c64"] = decisiones_c64

    monkeypatch.setattr(fa, "autorizar_casos", fake_autorizar_casos)

    app = create_app()

    class RunNow:
        calls: list[str] = []

        def run(self, tarea, *, kind, num_doc=None):
            self.calls.append(kind)
            tarea(lambda _m: None)
            return "job-xyz"

    app.state.jobs = RunNow()
    client = TestClient(app)

    resp = client.post(
        "/api/procesos/autorizar",
        json={
            "lineas": ["111"],
            "decisiones": {"111": {"accion": "aplicar_c89"}},
            "decisiones_c64": {"222": {"accion": "aplicar_g58"}},
        },
    )
    assert resp.status_code == 200
    assert capturado["lineas"] == ["111"]
    assert capturado["decisiones"] == {"111": {"accion": "aplicar_c89", "valor": None}}
    assert capturado["decisiones_c64"] == {"222": {"accion": "aplicar_g58", "valor": None}}


def test_post_archivar_valida_body() -> None:
    client, _ = _client_with_fake()
    resp = client.post("/api/procesos/archivar", json={})
    assert resp.status_code == 422


def test_post_autorizar_pre_check_devuelve_conflictos(monkeypatch) -> None:
    import MACRO.flujos.flujo_autorizar as fa

    monkeypatch.setattr(
        fa, "prechequear_autorizar",
        lambda lineas: {
            "c65": [{"num_doc": "111", "per_doc": "202413",
                     "nombre": "PEREZ JUAN", "c89": 500.0}],
            "c64": [{"num_doc": "222", "per_doc": "202413",
                     "nombre": "GOMEZ ANA", "g58": 1475.0}],
        },
    )
    client, _ = _client_with_fake()
    resp = client.post("/api/procesos/autorizar/pre-check",
                       json={"lineas": ["111", "222"]})
    assert resp.status_code == 200
    assert resp.json() == {
        "conflictos": [{"num_doc": "111", "per_doc": "202413",
                        "nombre": "PEREZ JUAN", "c89": 500.0}],
        "conflictos_c64": [{"num_doc": "222", "per_doc": "202413",
                            "nombre": "GOMEZ ANA", "g58": 1475.0}],
    }


def test_post_verificar_repositorio_sincrono(monkeypatch) -> None:
    import MACRO.flujos.flujo_verificar_repositorio as fv

    monkeypatch.setattr(
        fv, "verificar_exp_repositorio",
        lambda num_docs, callback_progreso=None: {"casos": [{
            "num_doc": "111", "num_dev": "D", "num_ruc": "R", "nombre": "N",
            "tipo_exp": "ELECTRONICO",
            "repositorios": [
                {"denom": "000-URD999-2026-1-1", "clasificacion": "VIA_ESPECIAL",
                 "estado": "subido", "subible": False},
                {"denom": "000-URD999-2026-2-1", "clasificacion": "VIA_ESPECIAL",
                 "estado": "pendiente_subir", "subible": True},
            ],
            "sin_repositorio": False, "error": "",
        }]},
    )
    client, _ = _client_with_fake()
    resp = client.post("/api/procesos/verificar-repositorio", json={"num_docs": ["111"]})
    assert resp.status_code == 200
    caso = resp.json()["casos"][0]
    assert caso["tipo_exp"] == "ELECTRONICO"
    est = {e["denom"]: e for e in caso["repositorios"]}
    assert est["000-URD999-2026-2-1"]["subible"] is True
    assert est["000-URD999-2026-1-1"]["estado"] == "subido"


def test_post_subir_repositorio_lanza_job() -> None:
    client, fake = _client_with_fake()
    resp = client.post(
        "/api/procesos/verificar-repositorio/subir",
        json={"items": [{"num_doc": "111", "num_dev": "D", "num_ruc": "R",
                         "denom": "000-URD999-2026-2-1"}]},
    )
    assert resp.status_code == 200
    assert fake.calls == ["subir_repositorio"]


def test_validar_archivo_emite_avance_por_caso(monkeypatch):
    """El endpoint es síncrono (el resultado es la respuesta), pero debe emitir
    progreso por WS: sin eso no se sabe si avanza sobre un lote grande."""
    import MACRO.flujos.flujo_validar_archivo as fv

    eventos = []
    docs = ["D1", "D2", "D3"]
    monkeypatch.setattr(fv, "obtener_datos_incluye_archivo",
                        lambda d: pd.DataFrame([{"num_doc": x, "cod_for": "1649"} for x in docs]))
    monkeypatch.setattr(fv, "verificar_y_conectar_servicios", lambda **kw: (None, None, False))
    monkeypatch.setattr(fv, "num_docs_archivados", lambda d: [])
    monkeypatch.setattr(fv, "ofs_all_electronicas", lambda ofs: set())
    monkeypatch.setattr(fv, "_evaluar_un_caso",
                        lambda *a, **k: {"num_doc": "X", "alertas": [], "nivel": "ok"})

    fv.validar_casos(docs, callback_progreso=eventos.append)

    avances = [e for e in eventos if isinstance(e, dict) and "done" in e]
    assert [e["done"] for e in avances] == [0, 1, 2, 3]
    assert {e["total"] for e in avances} == {3}
    assert avances[-1]["etiqueta"] == "D3"
