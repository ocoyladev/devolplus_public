"""Esquemas del registro de cartas por solicitud."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

TipoCarta = Literal["PRIMERA", "REITERATIVA", "AMPLIACION", "OTRA", ""]


class CartaIn(BaseModel):
    """Campos editables de una carta. Todo opcional: en PATCH solo se envía
    lo que cambia, y lo ausente no se toca."""

    numero: str | None = None
    anio: str | None = None
    tipo: TipoCarta | None = None
    fecha_emision: str | None = None
    fecha_notificacion: str | None = None
    plazo: int | None = Field(default=None, gt=0)
    fecha_vencimiento: str | None = None
    atendida: bool | None = None
    obs: str | None = None

    @field_validator("fecha_emision", "fecha_notificacion", "fecha_vencimiento")
    @classmethod
    def _validar_fecha(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return v
        try:
            datetime.strptime(v, "%d/%m/%Y")
        except ValueError:
            raise ValueError("La fecha debe tener el formato DD/MM/YYYY") from None
        return v


class CartaOut(BaseModel):
    id: int
    num_doc: str
    numero: str = ""
    anio: str = ""
    tipo: str = ""
    fecha_emision: str = ""
    fecha_notificacion: str = ""
    plazo: int | None = None
    fecha_vencimiento: str = ""
    vencimiento_manual: int = 0
    atendida: int = 0
    obs: str = ""
    estado: str


class CartasResponse(BaseModel):
    cartas: list[CartaOut]


class OkResponse(BaseModel):
    ok: bool
