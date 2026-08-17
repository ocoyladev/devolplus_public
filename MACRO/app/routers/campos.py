"""Router de edición inline de campos: PATCH /api/campos/{num_doc}."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from MACRO.app.schemas.campos import (
    CAMPO_A_DESTINO,
    ActualizarCampoRequest,
    ActualizarCampoResponse,
)

router = APIRouter(prefix="/api/campos", tags=["campos"])


@router.patch("/{num_doc}", response_model=ActualizarCampoResponse)
def actualizar_campo(num_doc: str, body: ActualizarCampoRequest) -> ActualizarCampoResponse:
    """Persiste el valor de un campo editable en SQLite.

    Reemplaza los handlers Flet ``actualizar_resultado`` / ``actualizar_ri`` /
    ``actualizar_carta`` / ``actualizar_observaciones`` / ``actualizar_ind_for_dev``,
    todos delgados sobre ``database.actualizar_dato_celda``.
    """
    from MACRO import database  # import diferido: evita coste si la API no se usa

    tabla, columna = CAMPO_A_DESTINO[body.campo]
    ok = database.actualizar_dato_celda(tabla, columna, body.valor, num_doc)
    if not ok:
        raise HTTPException(status_code=500, detail="No se pudo actualizar el campo")
    return ActualizarCampoResponse(
        ok=True, num_doc=num_doc, campo=body.campo, valor=body.valor
    )
