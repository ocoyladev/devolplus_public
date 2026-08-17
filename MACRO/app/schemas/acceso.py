"""Esquemas del control de acceso (verificación Oracle + solicitud)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

EstadoAcceso = Literal[
    "permitido",
    "no_registrado",
    "pendiente",
    "rechazado",
    "inactivo",
    "sin_conexion",
]


class AccesoEstado(BaseModel):
    estado: EstadoAcceso
    usuario_red: str
    mensaje: str


class SolicitudAccesoRequest(BaseModel):
    nombre_completo: str
    # Correo institucional obligatorio; el dominio se valida en el servicio
    # (auth_service.solicitar_acceso) para devolver un mensaje amigable en vez
    # de un 422 de Pydantic.
    email: str


class AccesoResultado(BaseModel):
    ok: bool
    mensaje: str
