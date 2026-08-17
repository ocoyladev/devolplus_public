"""Esquema del estado del entorno de ejecución (pantalla / firma automática)."""
from __future__ import annotations

from pydantic import BaseModel


class FirmaAutoEstado(BaseModel):
    """Disponibilidad de la firma automática por coordenadas.

    La secuencia de clics está calibrada por perfil de pantalla; solo se
    admiten dos combinaciones exactas de escala/resolución física: 125% con
    1920×1200, o 100% con 1920×1080. Fuera de esos perfiles, no está
    disponible.
    """

    disponible: bool
    escala: int | None = None
    ancho: int | None = None
    alto: int | None = None
    motivo: str = ""
    perfil: str | None = None
