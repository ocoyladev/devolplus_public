"""Router del entorno de ejecución (detección de pantalla para firma automática)."""
from __future__ import annotations

from fastapi import APIRouter

from MACRO import entorno_pantalla
from MACRO.app.schemas.entorno import FirmaAutoEstado

router = APIRouter(prefix="/api/entorno", tags=["entorno"])


def _detectar_pantalla() -> FirmaAutoEstado:
    """Estado de la firma automática según el perfil de pantalla detectado."""
    lec = entorno_pantalla.leer_pantalla()
    if lec.escala is None or lec.ancho is None or lec.alto is None:
        return FirmaAutoEstado(
            disponible=False,
            escala=lec.escala,
            ancho=lec.ancho,
            alto=lec.alto,
            motivo=lec.error or "No se pudo detectar la pantalla.",
        )
    perfil = entorno_pantalla.perfil_para(lec.escala, lec.ancho, lec.alto)
    disponible = perfil is not None
    motivo = (
        ""
        if disponible
        else (
            f"Requiere {entorno_pantalla.perfiles_admitidos_texto()} "
            f"(detectado: {lec.escala}% y {lec.ancho}×{lec.alto})."
        )
    )
    return FirmaAutoEstado(
        disponible=disponible,
        escala=lec.escala,
        ancho=lec.ancho,
        alto=lec.alto,
        motivo=motivo,
        perfil=(perfil.clave if perfil else None),
    )


@router.get("/firma-auto", response_model=FirmaAutoEstado)
def firma_auto() -> FirmaAutoEstado:
    """Indica si la firma automática por coordenadas puede activarse.

    Se consulta una sola vez al iniciar el frontend. La verificación es de solo
    lectura y no altera el estado del sistema.
    """
    return _detectar_pantalla()
