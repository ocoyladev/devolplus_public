"""Esquemas compartidos por varios routers."""
from __future__ import annotations

from pydantic import BaseModel


class JobResponse(BaseModel):
    """Respuesta inmediata de un endpoint de larga duración."""

    job_id: str
