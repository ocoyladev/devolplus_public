"""Esquemas de mantenimiento: borrado de BD/descargas y gestión de la cola."""
from __future__ import annotations

from pydantic import BaseModel


class IdsRequest(BaseModel):
    ids: list[int]


class DescargaColaItem(BaseModel):
    id: int
    num_doc: str | None = None
    ruc: str | None = None
    tipo_servicio: str | None = None
    tipo_descarga: str | None = None
    parametro: str | None = None
    estado: str | None = None
    reintentos: int | None = None
    error_log: str | None = None


class DescargasColaResponse(BaseModel):
    descargas: list[DescargaColaItem]


class ArchivarRepositorioItem(BaseModel):
    id: int
    num_doc: str | None = None
    ruc: str | None = None
    num_ri: str | None = None
    aduana: str | None = None
    urd: str | None = None
    anio: str | None = None
    nroexpedi: str | None = None
    denom: str | None = None
    estado: str | None = None
    mensaje: str | None = None
    fecha_registro: str | None = None


class ArchivarRepositorioColaResponse(BaseModel):
    pendientes: list[ArchivarRepositorioItem]


class BorrarCasoRequest(BaseModel):
    num_doc: str
    borrar_carpeta: bool = False


class BorrarCasoResponse(BaseModel):
    eliminadas: dict[str, int]
    carpeta_borrada: bool
    carpeta: str = ""
