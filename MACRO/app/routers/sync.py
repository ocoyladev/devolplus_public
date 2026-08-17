"""Router de sincronización de datos (desde MACROs / BD remota). Jobs."""
from __future__ import annotations

from fastapi import APIRouter, Request

from MACRO.app.schemas.common import JobResponse

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/macros", response_model=JobResponse)
def sync_macros(request: Request) -> JobResponse:
    """Actualiza la BD local a partir de los archivos MACRO de cada caso."""
    from MACRO.flujos.flujo_sync import actualizar_desde_macros

    def tarea(progreso):
        return actualizar_desde_macros(progreso)

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="sync_macros"))


@router.post("/remota", response_model=JobResponse)
def sync_remota(request: Request) -> JobResponse:
    """Actualiza la BD local según la BD remota (RSIRAT/Workflow)."""
    from MACRO.flujos.flujo_sync import actualizar_segun_bd_remota

    def tarea(progreso):
        return actualizar_segun_bd_remota(progreso)

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="sync_remota"))
