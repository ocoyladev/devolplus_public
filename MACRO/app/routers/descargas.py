"""Router de descargas por fila / masivas (jobs en background)."""
from __future__ import annotations

from fastapi import APIRouter, Request

from MACRO.app.schemas.common import JobResponse
from MACRO.app.schemas.descargas import (
    Descarga3uitRequest,
    DescargaCartaMasivoRequest,
    DescargaCartaRequest,
    DescargaRepositorioRequest,
    DescargaEjerciciosRequest,
    DescargaExpElectronicoRequest,
    DescargaPlaneamientoRequest,
    DescargaRiMasivoRequest,
    DescargaRiRequest,
    NumeracionCartasRequest,
    SistemaLegacyMasivoRequest,
    SistemaLegacyPreflightRequest,
)

router = APIRouter(prefix="/api/descargas", tags=["descargas"])


@router.post("/repositorio", response_model=JobResponse)
def descargar_repositorio(body: DescargaRepositorioRequest, request: Request) -> JobResponse:
    """Lanza la descarga de expediente(s) E-Doc para un caso (job)."""
    from MACRO.flujos.flujo_repositorio import descargar_expedientes_caso

    num_doc = str(body.row.get("num_doc", "")).strip()

    def tarea(progreso):
        return descargar_expedientes_caso(body.row, body.expedientes, progreso)

    job_id = request.app.state.jobs.run(tarea, kind="descarga_repositorio", num_doc=num_doc)
    return JobResponse(job_id=job_id)


@router.post("/reintentar", response_model=JobResponse)
def reintentar(request: Request) -> JobResponse:
    """Reprocesa las descargas pendientes en la cola (job)."""
    from MACRO.flujos.flujo_asignacion_excel import reintentar_descargas_pendientes

    def tarea(progreso):
        return reintentar_descargas_pendientes(callback_progreso=progreso)

    return JobResponse(
        job_id=request.app.state.jobs.run(tarea, kind="reintentar_descargas")
    )


@router.post("/ri", response_model=JobResponse)
def descargar_ri(body: DescargaRiRequest, request: Request) -> JobResponse:
    """Lanza la descarga de RI + notificación de RI para un caso (job)."""
    from MACRO.flujos.flujo_descargas import descargar_ri_caso

    num_doc = str(body.row.get("num_doc", "")).strip()

    def tarea(progreso):
        return descargar_ri_caso(body.row, body.ri_valor, progreso, archivo=body.archivo)

    job_id = request.app.state.jobs.run(tarea, kind="descarga_ri", num_doc=num_doc)
    return JobResponse(job_id=job_id)


@router.post("/ri-masivo", response_model=JobResponse)
def descargar_ri_masivo_endpoint(body: DescargaRiMasivoRequest, request: Request) -> JobResponse:
    """Descarga RI para varias filas seleccionadas (job)."""
    from MACRO.flujos.flujo_descargas import descargar_ri_masivo

    def tarea(progreso):
        return descargar_ri_masivo(body.filas, archivo=body.archivo, callback_progreso=progreso)

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="descarga_ri"))


@router.post("/cartas", response_model=JobResponse)
def descargar_cartas(body: DescargaCartaRequest, request: Request) -> JobResponse:
    """Lanza la descarga de carta(s) + notificación(es) para un caso (job)."""
    from MACRO.flujos.flujo_descargas import descargar_cartas_caso

    num_doc = str(body.row.get("num_doc", "")).strip()

    def tarea(progreso):
        return descargar_cartas_caso(body.row, body.cartas_valor, progreso, archivo=body.archivo)

    job_id = request.app.state.jobs.run(tarea, kind="descarga_cartas", num_doc=num_doc)
    return JobResponse(job_id=job_id)


@router.post("/cartas-masivo", response_model=JobResponse)
def descargar_cartas_masivo_endpoint(body: DescargaCartaMasivoRequest, request: Request) -> JobResponse:
    """Descarga carta(s) para varias filas seleccionadas (job)."""
    from MACRO.flujos.flujo_descargas import descargar_cartas_masivo

    def tarea(progreso):
        return descargar_cartas_masivo(body.filas, archivo=body.archivo, callback_progreso=progreso)

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="descarga_cartas_masivo"))


@router.post("/exp-electronico", response_model=JobResponse)
def descargar_exp_electronico(
    body: DescargaExpElectronicoRequest, request: Request
) -> JobResponse:
    """Lanza la descarga del Expediente Electrónico de un caso (job)."""
    from MACRO.flujos.flujo_descargas import descargar_exp_electronico_caso

    num_doc = str(body.row.get("num_doc", "")).strip()

    def tarea(progreso):
        return descargar_exp_electronico_caso(body.row, progreso)

    job_id = request.app.state.jobs.run(
        tarea, kind="descarga_exp_electronico", num_doc=num_doc
    )
    return JobResponse(job_id=job_id)


@router.post("/3uit", response_model=JobResponse)
def descargar_3uit(body: Descarga3uitRequest, request: Request) -> JobResponse:
    """Lanza la descarga 3UIT - Casilla 514 para un caso (job)."""
    from MACRO.flujos.flujo_descargas import descargar_3uit_caso

    num_doc = str(body.row.get("num_doc", "")).strip()

    def tarea(progreso):
        return descargar_3uit_caso(body.row, body.num_formulario, progreso)

    job_id = request.app.state.jobs.run(tarea, kind="descarga_3uit", num_doc=num_doc)
    return JobResponse(job_id=job_id)


@router.post("/planeamiento", response_model=JobResponse)
def descargar_planeamiento(
    body: DescargaPlaneamientoRequest, request: Request
) -> JobResponse:
    """Lanza la descarga del reporte de Planeamiento (Workflow) para un RUC (job)."""
    from MACRO.flujos.flujo_descargas import descargar_planeamiento_caso

    num_doc = str(body.row.get("num_doc", "")).strip()

    def tarea(progreso):
        return descargar_planeamiento_caso(body.row, body.ruc, progreso)

    job_id = request.app.state.jobs.run(
        tarea, kind="descarga_planeamiento", num_doc=num_doc
    )
    return JobResponse(job_id=job_id)


@router.post("/numeracion", response_model=JobResponse)
def agregar_numeracion(body: NumeracionCartasRequest, request: Request) -> JobResponse:
    """Agrega la numeración a las cartas generadas de las filas seleccionadas (job)."""
    from MACRO.flujos.flujo_descargas import agregar_numeracion_cartas

    def tarea(progreso):
        return agregar_numeracion_cartas(body.filas, progreso)

    return JobResponse(
        job_id=request.app.state.jobs.run(tarea, kind="numeracion_cartas")
    )


@router.post("/ejercicios", response_model=JobResponse)
def descargar_ejercicios(body: DescargaEjerciciosRequest, request: Request) -> JobResponse:
    """Lanza la descarga 'Por ejercicio(s)' (RELIQ-ALL) de un caso (job)."""
    from MACRO.flujos.flujo_descargas import descargar_por_ejercicios_caso

    num_doc = str(body.row.get("num_doc", "")).strip()

    def tarea(progreso):
        return descargar_por_ejercicios_caso(body.row, body.count, progreso)

    job_id = request.app.state.jobs.run(tarea, kind="descarga_ejercicios", num_doc=num_doc)
    return JobResponse(job_id=job_id)


@router.post("/sistema-legacy-ref", response_model=JobResponse)
def descargar_sistema_legacy_ref(body: SistemaLegacyMasivoRequest, request: Request) -> JobResponse:
    """Descarga REF/Tiempos de las filas seleccionadas vía SISTEMA_LEGACY (job)."""
    from MACRO.flujos.flujo_sistema_legacy import descargar_ref_tiempos_sistema_legacy

    def tarea(progreso):
        return descargar_ref_tiempos_sistema_legacy(body.filas, callback_progreso=progreso)

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="sistema_legacy_ref"))


@router.post("/sistema-legacy-antecedentes", response_model=JobResponse)
def descargar_sistema_legacy_antecedentes(body: SistemaLegacyMasivoRequest, request: Request) -> JobResponse:
    """Descarga los antecedentes de fiscalización (Fichas REF) vía SISTEMA_LEGACY (job)."""
    from MACRO.flujos.flujo_sistema_legacy import descargar_antecedentes_sistema_legacy

    def tarea(progreso):
        return descargar_antecedentes_sistema_legacy(body.filas, callback_progreso=progreso)

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="sistema_legacy_antec"))


@router.post("/sistema-legacy-preflight")
def preflight_sistema_legacy(body: SistemaLegacyPreflightRequest) -> dict:
    """Qué casos de la selección requieren correr SISTEMA_LEGACY y cuáles ya están descargados.

    Síncrono (no crea job): lo consulta la ventana de confirmación antes de lanzar
    la automatización. Para 'antec' parsea el planeamiento de cada caso, así que
    puede tardar un par de segundos con selecciones grandes.
    """
    from MACRO.flujos.flujo_sistema_legacy import verificar_pendientes_sistema_legacy

    return verificar_pendientes_sistema_legacy(body.tipo, body.filas)
