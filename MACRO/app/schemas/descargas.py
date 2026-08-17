"""Esquemas de las descargas por fila / masivas."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class DescargaEchasquiRequest(BaseModel):
    # Fila de la grilla (provee of_devolucion/ruc/nombre/num_doc/is_of_multiple
    # que get_case_folder necesita para ubicar la carpeta del caso).
    row: dict[str, Any]
    expedientes: list[str]


class DescargaRiRequest(BaseModel):
    row: dict[str, Any]
    # Si se omite, se toma de la fila (num_ri / ri).
    ri_valor: str | None = None
    # Si True, descarga en la carpeta de archivo (caso archivado).
    archivo: bool = False


class DescargaCartaRequest(BaseModel):
    row: dict[str, Any]
    # Texto 'numero-anio, ...'. Si se omite, se toma de la fila (carta).
    cartas_valor: str | None = None
    archivo: bool = False


class DescargaRiMasivoRequest(BaseModel):
    filas: list[dict[str, Any]]
    archivo: bool = False


class DescargaCartaMasivoRequest(BaseModel):
    filas: list[dict[str, Any]]
    archivo: bool = False


class DescargaExpElectronicoRequest(BaseModel):
    row: dict[str, Any]


class Descarga3uitRequest(BaseModel):
    row: dict[str, Any]
    # N° de orden del formulario. Si se omite, se toma de la fila (num_doc_aso).
    num_formulario: str | None = None


class DescargaEjerciciosRequest(BaseModel):
    row: dict[str, Any]
    count: int = 1  # cantidad de ejercicios previos a descargar


class DescargaPlaneamientoRequest(BaseModel):
    row: dict[str, Any]
    # RUC ingresado por el usuario; define el nombre del PDF resultante.
    ruc: str


class NumeracionCartasRequest(BaseModel):
    # Filas seleccionadas; cada una provee 'carta' y los campos que
    # get_case_folder necesita para ubicar la carpeta del caso.
    filas: list[dict[str, Any]]


class RsiratMasivoRequest(BaseModel):
    # Filas seleccionadas; cada una provee of_devolucion/ruc/nombre/periodo
    # (per_doc) para la automatización RSIRAT (REF/Tiempos o Antecedentes).
    filas: list[dict[str, Any]]


class RsiratPreflightRequest(BaseModel):
    # 'ref' (REF + Reporte de Tareas) o 'antec' (Fichas REF).
    tipo: Literal["ref", "antec"]
    filas: list[dict[str, Any]]
