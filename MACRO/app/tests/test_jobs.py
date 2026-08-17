import threading

from MACRO.app.jobs import JobManager


def _collector():
    lock = threading.Lock()
    eventos: list[dict] = []

    def emit(msg: dict) -> None:
        with lock:
            eventos.append(msg)

    return eventos, emit


def test_job_exitoso_emite_progreso_y_done() -> None:
    eventos, emit = _collector()
    jm = JobManager(emit)

    def tarea(progreso):
        progreso("paso 1")
        progreso("paso 2")
        return "listo"

    job_id = jm.run(tarea, kind="descarga_ri", num_doc="123")
    jm.join(job_id, timeout=5)

    tipos = [(e["type"], e.get("msg") or e.get("ok")) for e in eventos]
    assert tipos == [
        ("progress", "paso 1"),
        ("progress", "paso 2"),
        ("job_done", True),
    ]
    assert all(e["job_id"] == job_id for e in eventos)
    assert all(e["num_doc"] == "123" for e in eventos)
    assert eventos[0]["kind"] == "descarga_ri"


def test_job_que_retorna_exito_false_emite_done_fallido() -> None:
    eventos, emit = _collector()
    jm = JobManager(emit)

    def tarea(progreso):
        progreso("trabajando")
        return {"exito": False, "mensaje": "no hay datos"}

    job_id = jm.run(tarea, kind="x")
    jm.join(job_id, timeout=5)

    done = eventos[-1]
    assert done["type"] == "job_done"
    assert done["ok"] is False
    assert "no hay datos" in done["error"]


def test_job_que_retorna_exito_true_incluye_mensaje() -> None:
    eventos, emit = _collector()
    jm = JobManager(emit)

    def tarea(progreso):
        return {"exito": True, "mensaje": "documento generado"}

    job_id = jm.run(tarea, kind="x")
    jm.join(job_id, timeout=5)

    done = eventos[-1]
    assert done["ok"] is True
    assert done["mensaje"] == "documento generado"


def test_job_papeles_trabajo_exito_parcial_propaga_errores_y_ok_count() -> None:
    eventos, emit = _collector()
    jm = JobManager(emit)

    def tarea(progreso):
        return {
            "exito": True,
            "mensaje": "1/2 caso(s) OK. 1 con error.",
            "ok_count": 1,
            "errores": [{"caso": "OF 9 · doc 3", "motivo": "PAPELES_TRABAJO falló tras 3 intentos"}],
        }

    job_id = jm.run(tarea, kind="papeles_trabajo")
    jm.join(job_id, timeout=5)

    done = eventos[-1]
    assert done["ok"] is True
    assert done["ok_count"] == 1
    assert done["errores"] == [
        {"caso": "OF 9 · doc 3", "motivo": "PAPELES_TRABAJO falló tras 3 intentos"}
    ]


def test_job_papeles_trabajo_todo_falla_propaga_errores_en_done_fallido() -> None:
    eventos, emit = _collector()
    jm = JobManager(emit)

    def tarea(progreso):
        return {
            "exito": False,
            "mensaje": "0/1 caso(s) OK. 1 con error.",
            "ok_count": 0,
            "errores": [{"caso": "OF 9", "motivo": "MACRO.xlsx no encontrado"}],
        }

    job_id = jm.run(tarea, kind="papeles_trabajo")
    jm.join(job_id, timeout=5)

    done = eventos[-1]
    assert done["ok"] is False
    assert done["ok_count"] == 0
    assert done["errores"] == [{"caso": "OF 9", "motivo": "MACRO.xlsx no encontrado"}]


def test_job_archivar_conteo_int_no_rompe_y_emite_ok() -> None:
    # Regresión: 'Archivar' devuelve un conteo (int). No debe tratarse como la
    # lista 'archivados' de 'Cargar datos' (evita TypeError -> job_done ok:false,
    # que dejaba la tabla sin refrescar).
    eventos, emit = _collector()
    jm = JobManager(emit)

    def tarea(progreso):
        return {"exito": True, "mensaje": "Casos archivados: 3.", "n_archivados": 3}

    job_id = jm.run(tarea, kind="archivar")
    jm.join(job_id, timeout=5)

    done = eventos[-1]
    assert done["ok"] is True
    assert "archivados" not in done  # el conteo no viaja como lista


def test_job_archivados_lista_se_propaga() -> None:
    # 'Cargar datos' sí devuelve una lista de preexistentes en archivo.
    eventos, emit = _collector()
    jm = JobManager(emit)

    def tarea(progreso):
        return {"exito": True, "mensaje": "ok", "archivados": ["3001", "3002"]}

    job_id = jm.run(tarea, kind="carga_expedientes")
    jm.join(job_id, timeout=5)

    done = eventos[-1]
    assert done["ok"] is True
    assert done["archivados"] == ["3001", "3002"]


def test_job_archivados_int_bajo_clave_vieja_se_ignora() -> None:
    # Aunque un flujo dejara 'archivados' como int, el guard lo ignora sin romper.
    eventos, emit = _collector()
    jm = JobManager(emit)

    def tarea(progreso):
        return {"exito": True, "mensaje": "ok", "archivados": 3}

    job_id = jm.run(tarea, kind="archivar")
    jm.join(job_id, timeout=5)

    done = eventos[-1]
    assert done["ok"] is True
    assert "archivados" not in done


def test_job_con_excepcion_emite_done_con_error() -> None:
    eventos, emit = _collector()
    jm = JobManager(emit)

    def tarea(progreso):
        progreso("empezando")
        raise ValueError("algo falló")

    job_id = jm.run(tarea, kind="papeles_trabajo")
    jm.join(job_id, timeout=5)

    assert eventos[0]["type"] == "progress"
    done = eventos[-1]
    assert done["type"] == "job_done"
    assert done["ok"] is False
    assert "algo falló" in done["error"]


def test_progreso_dict_emite_campos_estructurados() -> None:
    eventos, emit = _collector()
    jm = JobManager(emit)

    def tarea(progreso):
        progreso({"done": 2, "total": 5, "etiqueta": "OF 123"})
        progreso("texto suelto")
        return {"exito": True, "mensaje": "ok"}

    job_id = jm.run(tarea, kind="x")
    jm.join(job_id, timeout=5)
    prog = [e for e in eventos if e["type"] == "progress"]
    assert prog[0]["done"] == 2 and prog[0]["total"] == 5 and prog[0]["etiqueta"] == "OF 123"
    assert prog[1]["msg"] == "texto suelto"
