"""El JobManager reenvía oks/ya_descargadas/omitidos en job_done."""
from MACRO.app.jobs import JobManager


def test_job_done_incluye_oks_y_extras():
    eventos = []
    jm = JobManager(emit=eventos.append)

    def tarea(_progreso):
        return {
            "exito": True, "mensaje": "ok", "ok_count": 2,
            "oks": ["D1", "D2"], "ya_descargadas": ["D3"], "omitidos": ["D4"],
        }

    jid = jm.run(tarea, kind="descarga_cartas")
    jm.join(jid, timeout=2)
    done = [e for e in eventos if e["type"] == "job_done"][0]
    assert done["oks"] == ["D1", "D2"]
    assert done["ya_descargadas"] == ["D3"]
    assert done["omitidos"] == ["D4"]


def test_job_done_fallido_incluye_oks_y_extras():
    """Un resultado con exito=False también debe reenviar oks/ya_descargadas/omitidos."""
    eventos = []
    jm = JobManager(emit=eventos.append)

    def tarea(_progreso):
        return {
            "exito": False, "mensaje": "falló parcialmente",
            "oks": ["D1"], "ya_descargadas": ["D2"], "omitidos": ["D3"],
        }

    jid = jm.run(tarea, kind="descarga_cartas_masivo")
    jm.join(jid, timeout=2)
    done = [e for e in eventos if e["type"] == "job_done"][0]
    assert done["ok"] is False
    assert done["oks"] == ["D1"]
    assert done["ya_descargadas"] == ["D2"]
    assert done["omitidos"] == ["D3"]
