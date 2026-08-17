"""Router de tickets Mesa de Ayuda (jobs en background)."""
from __future__ import annotations

from fastapi import APIRouter, Request

from MACRO.app.schemas.common import JobResponse
from MACRO.app.schemas.mesa_ayuda import (
    Empleador601,
    Empleadores601Request,
    Empleadores601Response,
    MesaAyudaDescargaRequest,
    MesaAyudaModificarRequest,
    MesaAyudaPreviewResponse,
)

router = APIRouter(prefix="/api/mesa-ayuda", tags=["mesa_ayuda"])


@router.post("/empleadores-601", response_model=Empleadores601Response)
def empleadores_601(body: Empleadores601Request) -> Empleadores601Response:
    """Extrae los empleadores (RUC, nombre) del PDT 601 desde el ZIP del caso.

    Lo usa el flujo Mesa de Ayuda 601 para no pedir el RUC manualmente cuando ya está en
    el archivo personalizado del caso.
    """
    from MACRO.flujos.flujo_mesa_ayuda import _per_doc, _ruc, extraer_empleadores_601
    from MACRO.funciones.funciones_casos import get_case_folder
    from MACRO.mesa_ayuda import periodos

    row = body.row
    try:
        carpeta = get_case_folder(row)
        ruc = _ruc(row)
        ejercicio = periodos.ejercicio_de_per_doc(_per_doc(row))
        pares = extraer_empleadores_601(carpeta, ruc, ejercicio)
    except Exception:  # noqa: BLE001 — si falla, lista vacía (el front pide manual)
        pares = []

    return Empleadores601Response(
        empleadores=[Empleador601(ruc=r, nombre=n) for r, n in pares]
    )


@router.post("/preview", response_model=MesaAyudaPreviewResponse)
def mesa_ayuda_preview(body: MesaAyudaDescargaRequest) -> MesaAyudaPreviewResponse:
    """Resumen del ticket a enviar (para el diálogo de confirmación).

    No registra nada en Mesa de Ayuda; solo calcula periodos, contenido del .txt y título
    con la misma lógica que la descarga real (fuente única).
    """
    from MACRO.flujos.flujo_mesa_ayuda import datos_descarga_desde_fila
    from MACRO.mesa_ayuda import tickets

    datos = datos_descarga_desde_fila(
        body.tipo,
        body.row,
        ruc_empleador=body.ruc_empleador,
        nombre_empleador=body.nombre_empleador,
        doc_override=body.doc_override,
    )
    ini, fin = tickets.resolver_periodos(datos)
    return MesaAyudaPreviewResponse(
        tipo=datos.tipo,
        of=datos.of,
        ruc=datos.ruc,
        nombre=datos.nombre,
        periodo_ini=ini,
        periodo_fin=fin,
        contenido_txt=tickets.contenido_txt(datos),
        titulo=tickets.titulo(datos),
    )


@router.post("/descarga", response_model=JobResponse)
def mesa_ayuda_descarga(body: MesaAyudaDescargaRequest, request: Request) -> JobResponse:
    """Registra un ticket Mesa de Ayuda de descarga (Rentas 4ta / 5ta / PDT 601)."""
    from MACRO.flujos.flujo_mesa_ayuda import datos_descarga_desde_fila, registrar_ticket

    num_doc = str(body.row.get("num_doc", "")).strip()

    def tarea(progreso):
        progreso(f"Registrando ticket Mesa de Ayuda ({body.tipo})…")
        datos = datos_descarga_desde_fila(
            body.tipo,
            body.row,
            ruc_empleador=body.ruc_empleador,
            nombre_empleador=body.nombre_empleador,
            doc_override=body.doc_override,
        )
        return registrar_ticket(datos)

    job_id = request.app.state.jobs.run(tarea, kind=f"mesa_ayuda_{body.tipo}", num_doc=num_doc)
    return JobResponse(job_id=job_id)


@router.post("/modificar", response_model=JobResponse)
def mesa_ayuda_modificar(body: MesaAyudaModificarRequest, request: Request) -> JobResponse:
    """Registra un ticket Mesa de Ayuda de modificación de modalidad de devolución."""
    from MACRO.flujos.flujo_mesa_ayuda import datos_modificar_desde_fila, registrar_ticket

    num_doc = str(body.row.get("num_doc", "")).strip()

    def tarea(progreso):
        progreso("Registrando modificación de modalidad…")
        datos = datos_modificar_desde_fila(body.row, body.modalidad, body.cci)
        return registrar_ticket(datos)

    job_id = request.app.state.jobs.run(tarea, kind="mesa_ayuda_modificar", num_doc=num_doc)
    return JobResponse(job_id=job_id)
