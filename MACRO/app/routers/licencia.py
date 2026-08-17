"""Router de licencia: estado y registro de la clave."""
from __future__ import annotations

from fastapi import APIRouter

from MACRO.app.schemas.config import (
    GuardarLicenciaRequest,
    LicenciaEstado,
    LicenciaResultado,
)

router = APIRouter(prefix="/api/licencia", tags=["licencia"])


@router.get("", response_model=LicenciaEstado)
def estado() -> LicenciaEstado:
    from MACRO.seguridad import verificar_licencia_existente

    valida, usuario, mensaje = verificar_licencia_existente()
    return LicenciaEstado(valida=valida, usuario=usuario, mensaje=mensaje)


@router.post("", response_model=LicenciaResultado)
def registrar(body: GuardarLicenciaRequest) -> LicenciaResultado:
    from MACRO.seguridad import guardar_licencia

    ok, mensaje = guardar_licencia(body.clave)
    return LicenciaResultado(ok=ok, mensaje=mensaje)
