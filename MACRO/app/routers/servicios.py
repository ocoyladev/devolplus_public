"""Router de verificación de servicios (estado de login Portal / Workflow)."""
from __future__ import annotations

from fastapi import APIRouter

from MACRO.app.schemas.servicios import ServiciosEstado

router = APIRouter(prefix="/api/servicios", tags=["servicios"])


@router.post("/verificar", response_model=ServiciosEstado)
def verificar() -> ServiciosEstado:
    """Intenta loguear en Portal y Workflow; devuelve el estado de cada uno.

    Reemplaza el indicador de la barra de estado de la GUI Flet. Corre en el
    threadpool de FastAPI (endpoint síncrono), por lo que no bloquea el loop.
    """
    from MACRO.flujos.flujo_asignacion_excel import verificar_y_conectar_servicios

    try:
        sesion, cookie, _ = verificar_y_conectar_servicios(
            check_portal=True, check_workflow=True
        )
        return ServiciosEstado(portal=sesion is not None, workflow=cookie is not None)
    except Exception:  # noqa: BLE001 — el estado simplemente queda en False
        return ServiciosEstado(portal=False, workflow=False)
