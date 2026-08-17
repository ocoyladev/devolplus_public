"""Esquemas de generación de documentos (Carta / RI)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ModelosResponse(BaseModel):
    modelos: list[str]


class GenerarCartaRequest(BaseModel):
    row: dict[str, Any]
    modelos: list[str] = []
    plazo: int = 3
    archivo: bool = False


class GenerarRiRequest(BaseModel):
    row: dict[str, Any]
    modelo: str
    num_ri: str | None = None
