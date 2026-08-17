"""Router de procesos masivos (archivar / recuperar / ...). Jobs en background."""
from __future__ import annotations

from fastapi import APIRouter, Request, Response

from MACRO.app.schemas.common import JobResponse
from MACRO.app.schemas.procesos import (
    AbrirCarpetaRequest,
    AutorizarRequest,
    CargaExpedientesRequest,
    ExportarRequest,
    PreCheckRequest,
    PreCheckResponse,
    ProcesoDocsRequest,
    SubirEchasquiRequest,
    SubsanarRequest,
    ValidarArchivoRequest,
    ValidarArchivoResponse,
    VerificarEchasquiRequest,
    VerificarEchasquiResponse,
)

router = APIRouter(prefix="/api/procesos", tags=["procesos"])


@router.post("/archivar", response_model=JobResponse)
def archivar(body: ProcesoDocsRequest, request: Request) -> JobResponse:
    """Archiva los casos indicados (mueve carpetas a PATH_ARCHIVO + BD)."""
    from MACRO.flujos.flujo_archivo import archivar_casos

    def tarea(progreso):
        return archivar_casos(body.num_docs, progreso)

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="archivar"))


@router.post("/recuperar", response_model=JobResponse)
def recuperar(body: ProcesoDocsRequest, request: Request) -> JobResponse:
    """Recupera casos del archivo (restaura BD + carpetas a PATH_DESCARGAS)."""
    from MACRO.flujos.flujo_archivo import recuperar_casos

    def tarea(progreso):
        return recuperar_casos(body.num_docs, progreso)

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="recuperar"))


@router.post("/pptt", response_model=JobResponse)
def generar_pptt(body: ProcesoDocsRequest, request: Request) -> JobResponse:
    """Genera el PPTT (REF/RI/MACRO consolidado) para los casos indicados.

    Nota: los prompts interactivos de contraseña de PDF (ECHASQUI) y de
    desempate OF_MULTIPLE se pasan como ``None`` (degradación elegante:
    intenta la clave derivada del RUC y omite los PDFs protegidos). El prompt
    interactivo por WebSocket queda como mejora futura.
    """
    from MACRO.flujos.flujo_generar_pptt import procesar_generar_pptt

    def tarea(progreso):
        return procesar_generar_pptt(
            body.num_docs,
            callback_progreso=progreso,
            solicitar_password=None,
            solicitar_eleccion=None,
        )

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="pptt"))


@router.post("/carga-expedientes", response_model=JobResponse)
def carga_expedientes(body: CargaExpedientesRequest, request: Request) -> JobResponse:
    """Carga masiva de expedientes electrónicos (Form. 1649) a Portal."""
    from MACRO.flujos.flujo_carga_expedientes import cargar_expedientes_electronicos

    def tarea(progreso):
        return cargar_expedientes_electronicos(
            body.num_docs, ejecutar_firma_auto=body.ejecutar_firma_auto, callback_progreso=progreso
        )

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="carga_expedientes"))


@router.post("/autorizar", response_model=JobResponse)
def autorizar(body: AutorizarRequest, request: Request) -> JobResponse:
    """Genera los documentos de autorización para los casos indicados (job)."""
    from MACRO.flujos.flujo_autorizar import autorizar_casos

    decisiones = {k: v.model_dump() for k, v in body.decisiones.items()}
    decisiones_c64 = {k: v.model_dump() for k, v in body.decisiones_c64.items()}

    def tarea(progreso):
        return autorizar_casos(body.lineas, decisiones, decisiones_c64, progreso)

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="autorizar"))


@router.post("/autorizar/pre-check", response_model=PreCheckResponse)
def autorizar_pre_check(body: PreCheckRequest) -> PreCheckResponse:
    """Escanea los MACRO y devuelve conflictos C89>0/C65==0 y C64==0."""
    from MACRO.flujos.flujo_autorizar import prechequear_autorizar

    res = prechequear_autorizar(body.lineas)
    return PreCheckResponse(conflictos=res["c65"], conflictos_c64=res["c64"])


@router.post("/verificar-echasqui", response_model=VerificarEchasquiResponse)
def verificar_echasqui(body: VerificarEchasquiRequest) -> VerificarEchasquiResponse:
    """Verifica qué echasqui electrónicos figuran en el expediente y cuáles no."""
    from MACRO.flujos.flujo_verificar_echasqui import verificar_exp_echasqui

    res = verificar_exp_echasqui(body.num_docs)
    return VerificarEchasquiResponse(casos=res["casos"])


@router.post("/archivar-echasqui", response_model=JobResponse)
def archivar_echasqui(body: ProcesoDocsRequest, request: Request) -> JobResponse:
    """Encola y ejecuta el archivado (ATENDIDO) de los echasqui de los casos."""
    from MACRO.flujos.flujo_archivar_echasqui import (
        encolar_archivar_echasqui, ejecutar_archivar_echasqui,
    )
    num_docs = list(body.num_docs)

    def tarea(progreso):
        enc = encolar_archivar_echasqui(num_docs)
        res = ejecutar_archivar_echasqui(enc["ids"], progreso)
        extra = ""
        if enc["omitidos"]:
            extra += f", {len(enc['omitidos'])} omitido(s) por datos faltantes"
        if enc.get("sin_exp"):
            extra += f", {len(enc['sin_exp'])} sin echasqui válido en la columna"
        res["mensaje"] = res.get("mensaje", "") + extra
        res["exito"] = True  # el resumen (detalle) se muestra siempre en el modal
        return res

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="archivar_echasqui"))


@router.post("/verificar-echasqui/subir", response_model=JobResponse)
def subir_echasqui(body: SubirEchasquiRequest, request: Request) -> JobResponse:
    """Sube por vía especial los echasqui electrónicos pendientes indicados (job)."""
    from MACRO.flujos.flujo_verificar_echasqui import subir_echasqui_pendientes

    items = [it.model_dump() for it in body.items]

    def tarea(progreso):
        return subir_echasqui_pendientes(items, progreso)

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="subir_echasqui"))


@router.post("/validar-archivo", response_model=ValidarArchivoResponse)
def validar_archivo(body: ValidarArchivoRequest, request: Request) -> ValidarArchivoResponse:
    """Valida (síncrono) cada caso/OF: PPTT, insumo final, Exp. ECHASQUI, carga
    1649 y elementos indispensables. Incluye casos archivados.

    El resultado es la propia respuesta, así que no es un job; aun así emite
    eventos ``progress`` por WebSocket para que la UI muestre el avance, que
    sobre muchos casos (una consulta a Portal por caso) puede tardar.
    """
    from MACRO.flujos.flujo_validar_archivo import validar_casos

    progreso = request.app.state.jobs.callback_sincrono(kind="validar_archivo")
    res = validar_casos(body.num_docs, callback_progreso=progreso)
    return ValidarArchivoResponse(casos=res["casos"])


@router.post("/validar-archivo/subsanar", response_model=JobResponse)
def validar_archivo_subsanar(body: SubsanarRequest, request: Request) -> JobResponse:
    """Ejecuta en background las acciones de subsanación indicadas."""
    from MACRO.flujos.flujo_validar_archivo import subsanar

    acciones = [a.model_dump() for a in body.acciones]

    def tarea(progreso):
        return subsanar(acciones, callback_progreso=progreso)

    return JobResponse(job_id=request.app.state.jobs.run(tarea, kind="validar_subsanar"))


@router.post("/validar-archivo/exportar", status_code=204)
def validar_archivo_exportar(body: ExportarRequest) -> Response:
    """Genera un .xlsx con el resumen y lo abre en el equipo (desktop)."""
    import os

    from MACRO.flujos.flujo_validar_archivo import exportar_resumen

    casos = [c.model_dump() for c in body.casos]
    ruta = exportar_resumen(casos)
    try:
        if hasattr(os, "startfile"):
            os.startfile(ruta)  # noqa: S606 — desktop Windows
    except Exception:
        pass
    return Response(status_code=204)


@router.post("/validar-archivo/abrir-carpeta", status_code=204)
def validar_archivo_abrir_carpeta(body: AbrirCarpetaRequest) -> Response:
    """Abre en el equipo la carpeta del caso (activa o archivo). Sin job/lock."""
    import os

    from MACRO.flujos.flujo_validar_archivo import _fila_de, resolver_carpeta_caso

    row = _fila_de(body.num_doc)
    if row is not None:
        _raiz, trabajo, existe, _ = resolver_carpeta_caso(row)
        try:
            if existe and hasattr(os, "startfile"):
                os.startfile(trabajo)  # noqa: S606 — desktop Windows
        except Exception:  # noqa: BLE001
            pass
    return Response(status_code=204)
