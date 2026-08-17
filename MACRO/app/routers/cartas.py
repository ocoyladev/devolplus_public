"""Router del registro de cartas: /api/cartas."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from MACRO.app.schemas.cartas import CartaIn, CartaOut, CartasResponse, OkResponse

router = APIRouter(prefix="/api/cartas", tags=["cartas"])


def _campos(body: CartaIn) -> dict:
    """Solo lo que el cliente envió: lo ausente no se toca."""
    return body.model_dump(exclude_unset=True)


@router.get("/{num_doc}", response_model=CartasResponse)
def listar(num_doc: str) -> CartasResponse:
    """Cartas del caso, más reciente primero, con su estado derivado."""
    from MACRO.funciones import funciones_registro_cartas as rc

    return CartasResponse(cartas=rc.listar_cartas(num_doc))


@router.post("/{num_doc}", response_model=CartaOut)
def crear(num_doc: str, body: CartaIn) -> CartaOut:
    """Registra una carta del caso. El número puede quedar vacío (borrador)."""
    from MACRO.funciones import funciones_registro_cartas as rc

    if not rc.caso_existe(num_doc):
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return CartaOut(**rc.crear_carta(num_doc, **_campos(body)))


@router.patch("/{id_carta}", response_model=CartaOut)
def actualizar(id_carta: int, body: CartaIn) -> CartaOut:
    """Actualiza una carta. Enviar `fecha_vencimiento` la fija a mano; enviarla
    vacía la devuelve al cálculo automático."""
    from MACRO.funciones import funciones_registro_cartas as rc

    carta = rc.actualizar_carta(id_carta, **_campos(body))
    if carta is None:
        raise HTTPException(status_code=404, detail="Carta no encontrada")
    return CartaOut(**carta)


@router.delete("/{id_carta}", response_model=OkResponse)
def eliminar(id_carta: int) -> OkResponse:
    """Elimina una carta (emitida por error) y reconstruye el espejo."""
    from MACRO.funciones import funciones_registro_cartas as rc

    if not rc.eliminar_carta(id_carta):
        raise HTTPException(status_code=404, detail="Carta no encontrada")
    return OkResponse(ok=True)
