"""Esquema del estado de login de servicios (Portal / Workflow)."""
from __future__ import annotations

from pydantic import BaseModel


class ServiciosEstado(BaseModel):
    portal: bool
    workflow: bool
