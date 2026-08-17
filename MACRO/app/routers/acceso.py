"""Router de acceso: verificación contra Oracle y autoregistro de solicitudes.

Reemplaza al router de licencia (clave-hash local) en la web app. El ``GET``
audita el intento de arranque en ``registro_logueos`` (efecto de lado esperado:
el frontend lo llama una sola vez al montar).
"""
from __future__ import annotations

from fastapi import APIRouter

from MACRO.app.schemas.acceso import (
    AccesoEstado,
    AccesoResultado,
    SolicitudAccesoRequest,
)

router = APIRouter(prefix="/api/acceso", tags=["acceso"])


@router.get("", response_model=AccesoEstado)
def estado() -> AccesoEstado:
    from MACRO.auth.auth_service import verificar_acceso

    r = verificar_acceso()
    return AccesoEstado(
        estado=r["estado"], usuario_red=r["usuario_red"], mensaje=r["mensaje"]
    )


@router.post("/solicitud", response_model=AccesoResultado)
def solicitud(body: SolicitudAccesoRequest) -> AccesoResultado:
    from MACRO.auth.auth_service import obtener_usuario_red, solicitar_acceso

    try:
        r = solicitar_acceso(
            nombre_completo=body.nombre_completo,
            usuario_red=obtener_usuario_red(),
            email=body.email,
        )
        return AccesoResultado(ok=r["ok"], mensaje=r["mensaje"])
    except Exception as exc:  # noqa: BLE001 — sin conexión u otro fallo de BD
        return AccesoResultado(
            ok=False,
            mensaje=(
                "No se pudo registrar la solicitud (sin conexión con la base de "
                f"datos). Reintente más tarde. Detalle: {exc}"
            ),
        )
