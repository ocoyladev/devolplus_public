"""Router de datos de la tabla: GET /api/datos/tabla."""
from __future__ import annotations

import json
import os
import tempfile

from fastapi import APIRouter, File, Form, Request, UploadFile

from MACRO.app.schemas.common import JobResponse
from MACRO.app.schemas.datos import CargarDatosRequest, TablaResponse

router = APIRouter(prefix="/api/datos", tags=["datos"])


def _serializar(df) -> TablaResponse:
    """Serializa un DataFrame de casos a TablaResponse (fechas DD/MM/YYYY)."""
    if df is None or df.empty:
        return TablaResponse(columns=[], rows=[], total=0)

    import pandas as pd

    # Las columnas datetime se formatean a DD/MM/YYYY ANTES de serializar; de lo
    # contrario df.to_json las convierte a epoch en milisegundos.
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%d/%m/%Y")

    rows = json.loads(df.to_json(orient="records"))
    return TablaResponse(columns=list(df.columns), rows=rows, total=len(rows))


@router.get("/planeamiento-estado")
def planeamiento_estado() -> dict:
    """Indica si en este momento se permiten descargas de planeamiento / SISTEMA_LEGACY.

    Bloqueado de lunes a viernes de 08:00 a 17:00 (hora de Lima). El frontend usa
    esto para deshabilitar el botón 'Archivo SISTEMA_LEGACY' dentro de ese horario.
    """
    from MACRO.funciones.funciones_generales import planeamiento_permitido

    return {"permitido": planeamiento_permitido()}


@router.get("/tabla", response_model=TablaResponse)
def obtener_tabla() -> TablaResponse:
    """Devuelve la tabla actual de casos (tabla_asign enriquecida) como registros JSON."""
    from MACRO.flujos.flujo_asignacion_excel import obtener_dataframe_actual

    return _serializar(obtener_dataframe_actual())


@router.get("/archivo", response_model=TablaResponse)
def obtener_archivo() -> TablaResponse:
    """Devuelve la tabla de casos ARCHIVADOS (tabla_asign_archivo)."""
    from MACRO.flujos.flujo_asignacion_excel import obtener_dataframe_archivo

    return _serializar(obtener_dataframe_archivo())


@router.post("/cargar", response_model=JobResponse)
def cargar(body: CargarDatosRequest, request: Request) -> JobResponse:
    """Carga casos a la BD local desde una lista de números de documento (job)."""
    from MACRO.flujos.flujo_cargar_datos_gui import cargar_datos_desde_lista

    def tarea(progreso):
        return cargar_datos_desde_lista(body.num_docs, callback_progreso=progreso)

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="cargar_datos"))


def _procesar_archivo(tipo: str, ruta: str, progreso):
    """Despacha el archivo subido al flujo de carga correspondiente."""
    if tipo == "asignacion":
        from MACRO.flujos.flujo_asignacion_excel import cargar_asignacion_excel

        return cargar_asignacion_excel(callback_progreso=progreso, ruta=ruta)
    if tipo == "sistema_legacy":
        from MACRO.flujos.flujo_asignacion_excel import cargar_sistema_legacy

        return cargar_sistema_legacy(callback_progreso=progreso, ruta=ruta)
    if tipo == "autorizacion":
        from MACRO.flujos.flujo_cargar_datos_gui import cargar_autorizacion_ri

        return cargar_autorizacion_ri(ruta, callback_progreso=progreso)
    return {"exito": False, "mensaje": f"Tipo de archivo desconocido: {tipo}"}


@router.post("/cargar-archivo", response_model=JobResponse)
async def cargar_archivo(
    request: Request,
    tipo: str = Form(...),
    file: UploadFile = File(...),
) -> JobResponse:
    """Carga datos desde un archivo subido (asignacion | sistema_legacy | autorizacion)."""
    suffix = os.path.splitext(file.filename or "")[1] or ".xlsx"
    contenido = await file.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(contenido)
    tmp.close()
    ruta = tmp.name

    def tarea(progreso):
        try:
            return _procesar_archivo(tipo, ruta, progreso)
        finally:
            try:
                os.unlink(ruta)
            except OSError:
                pass

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind=f"cargar_{tipo}"))
