"""Esquemas de los tickets Mesa de Ayuda (descarga 4ta/5ta/601 y modificar modalidad)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class MesaAyudaDescargaRequest(BaseModel):
    tipo: Literal["4ta", "5ta", "601", "601_completo"]
    row: dict[str, Any]
    # Solo para 601:
    ruc_empleador: str | None = None
    nombre_empleador: str | None = None
    doc_override: str | None = None


class MesaAyudaPreviewResponse(BaseModel):
    tipo: str
    of: str
    ruc: str
    nombre: str
    periodo_ini: int
    periodo_fin: int
    contenido_txt: str
    titulo: str


class MesaAyudaModificarRequest(BaseModel):
    row: dict[str, Any]
    modalidad: str
    cci: str | None = None


class Empleadores601Request(BaseModel):
    row: dict[str, Any]


class Empleador601(BaseModel):
    ruc: str
    nombre: str


class Empleadores601Response(BaseModel):
    empleadores: list[Empleador601]
