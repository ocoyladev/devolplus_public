"""Esquemas para la carga y lectura de la tabla de casos."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TablaResponse(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    total: int


class CargarDatosRequest(BaseModel):
    num_docs: list[str]
