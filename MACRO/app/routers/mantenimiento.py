"""Router de mantenimiento: borrado de BD/descargas y gestión de la cola de descargas."""
from __future__ import annotations

from fastapi import APIRouter, Request

from MACRO.app.schemas.common import JobResponse
from MACRO.app.schemas.mantenimiento import (
    ArchivarEchasquiColaResponse,
    BorrarCasoRequest,
    BorrarCasoResponse,
    DescargasColaResponse,
    IdsRequest,
)

router = APIRouter(prefix="/api/mantenimiento", tags=["mantenimiento"])


@router.get("/descargas", response_model=DescargasColaResponse)
def listar_descargas() -> DescargasColaResponse:
    """Lista las descargas de la cola no completadas (PENDIENTE/ERROR/EN_PROCESO)."""
    from MACRO.database import obtener_descargas_bd

    return DescargasColaResponse(descargas=obtener_descargas_bd())


@router.post("/descargas/eliminar")
def eliminar_descargas(body: IdsRequest) -> dict:
    """Elimina de la cola las descargas indicadas por sus id."""
    from MACRO.database import eliminar_descargas_bd

    return {"eliminadas": eliminar_descargas_bd(body.ids)}


@router.post("/descargas/ejecutar", response_model=JobResponse)
def ejecutar_descargas(body: IdsRequest, request: Request) -> JobResponse:
    """Ejecuta (reactivando a PENDIENTE) las descargas seleccionadas (job)."""
    from MACRO.database import reactivar_descargas_bd
    from MACRO.flujos.flujo_asignacion_excel import procesar_descargas_bd

    ids = list(body.ids)

    def tarea(progreso):
        reactivar_descargas_bd(ids)
        procesar_descargas_bd(callback_progreso_ui=progreso, ids=ids)
        return {"exito": True, "mensaje": f"Ejecutada(s) {len(ids)} descarga(s)."}

    return JobResponse(
        job_id=request.app.state.jobs.run(tarea, kind="descarga_seleccionada")
    )


@router.post("/borrar-bd")
def borrar_bd() -> dict:
    """Borra todos los datos de casos (tabla_asign, tabla_bd, registros, tracking)."""
    from MACRO.database import limpiar_tablas_asignacion

    limpiar_tablas_asignacion()
    return {"ok": True}


@router.post("/borrar-descargas")
def borrar_descargas() -> dict:
    """Vacía por completo la cola de descargas (tabla_desc)."""
    from MACRO.database import limpiar_tabla_desc_bd

    limpiar_tabla_desc_bd()
    return {"ok": True}


@router.post("/borrar-caso", response_model=BorrarCasoResponse)
def borrar_caso_endpoint(body: BorrarCasoRequest) -> BorrarCasoResponse:
    """Hard-delete de un caso por num_doc (BD + opcionalmente la carpeta)."""
    from MACRO.flujos.flujo_validar_archivo import borrar_caso_completo

    res = borrar_caso_completo(body.num_doc, body.borrar_carpeta)
    return BorrarCasoResponse(**res)


@router.get("/archivar-echasqui", response_model=ArchivarEchasquiColaResponse)
def listar_archivar_echasqui_endpoint() -> ArchivarEchasquiColaResponse:
    """Lista los pendientes de archivado echasqui."""
    from MACRO.database import listar_archivar_echasqui

    return ArchivarEchasquiColaResponse(pendientes=listar_archivar_echasqui())


@router.post("/archivar-echasqui/eliminar")
def eliminar_archivar_echasqui_endpoint(body: IdsRequest) -> dict:
    """Elimina pendientes de archivado echasqui por id."""
    from MACRO.database import eliminar_archivar_echasqui

    return {"eliminadas": eliminar_archivar_echasqui(body.ids)}


@router.post("/archivar-echasqui/ejecutar", response_model=JobResponse)
def ejecutar_archivar_echasqui_endpoint(body: IdsRequest, request: Request) -> JobResponse:
    """Reintenta el archivado de los pendientes seleccionados (job)."""
    from MACRO.flujos.flujo_archivar_echasqui import ejecutar_archivar_echasqui

    ids = list(body.ids)

    def tarea(progreso):
        return ejecutar_archivar_echasqui(ids, progreso)

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="archivar_echasqui"))
