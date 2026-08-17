"""Esquemas para la edición inline de campos de la tabla."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# Campos editables en la grilla y su mapeo a (tabla, columna) en SQLite.
CampoEditable = Literal["forma_dev", "resultado", "obs", "carta", "ri"]

CAMPO_A_DESTINO: dict[str, tuple[str, str]] = {
    "forma_dev": ("tabla_bd", "ind_for_dev"),
    "resultado": ("tabla_asign", "resultado"),
    "obs": ("tabla_asign", "obs_devol"),
    "carta": ("tabla_asign", "carta"),
    "ri": ("tabla_asign", "num_ri"),
}


class ActualizarCampoRequest(BaseModel):
    campo: CampoEditable
    valor: str


class ActualizarCampoResponse(BaseModel):
    ok: bool
    num_doc: str
    campo: CampoEditable
    valor: str
