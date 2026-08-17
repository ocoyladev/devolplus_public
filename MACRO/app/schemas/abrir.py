"""Esquemas para abrir archivos/carpetas del caso en el SO del usuario."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AbrirCasoRequest(BaseModel):
    row: dict[str, Any]
    archivo: bool = False  # True: abrir desde PATH_ARCHIVO (vista de archivo)


class AbrirResponse(BaseModel):
    ok: bool
    path: str
