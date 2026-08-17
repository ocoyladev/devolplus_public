"""Router de generación de documentos Carta / RI (modelos + jobs)."""
from __future__ import annotations

from fastapi import APIRouter, Request

from MACRO.app.schemas.common import JobResponse
from MACRO.app.schemas.generar import (
    GenerarCartaRequest,
    GenerarRiRequest,
    ModelosResponse,
)

router = APIRouter(prefix="/api/generar", tags=["generar"])


@router.get("/modelos/{tipo}", response_model=ModelosResponse)
def listar_modelos(tipo: str) -> ModelosResponse:
    """Lista los modelos .docx disponibles (tipo = carta | ri)."""
    from MACRO.flujos.flujo_documentos import listar_modelos as _listar

    return ModelosResponse(modelos=_listar(tipo))


@router.post("/carta", response_model=JobResponse)
def generar_carta(body: GenerarCartaRequest, request: Request) -> JobResponse:
    """Genera la Carta del caso (plantilla + modelos seleccionados + plazo)."""
    from MACRO.flujos.flujo_documentos import generar_carta_caso

    num_doc = str(body.row.get("num_doc", "")).strip()

    def tarea(progreso):
        return generar_carta_caso(body.row, body.modelos, body.plazo, progreso, archivo=body.archivo)

    return JobResponse(
        job_id=request.app.state.jobs.run(tarea, kind="generar_carta", num_doc=num_doc)
    )


@router.post("/ri", response_model=JobResponse)
def generar_ri(body: GenerarRiRequest, request: Request) -> JobResponse:
    """Genera el documento RI del caso (modelo + datos del caso)."""
    from MACRO.flujos.flujo_documentos import generar_ri_caso

    num_doc = str(body.row.get("num_doc", "")).strip()

    def tarea(progreso):
        return generar_ri_caso(body.row, body.modelo, body.num_ri, progreso)

    return JobResponse(
        job_id=request.app.state.jobs.run(tarea, kind="generar_ri", num_doc=num_doc)
    )
