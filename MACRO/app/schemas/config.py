"""Esquemas de configuración (rutas, credenciales) y licencia."""
from __future__ import annotations

from pydantic import BaseModel


class RutasConfig(BaseModel):
    PATH_DESCARGAS: str | None = None
    PATH_RI: str | None = None
    PATH_AUTORIZAR: str | None = None
    PATH_ARCHIVO: str | None = None
    PATH_SIRAT_EXE: str | None = None
    UNIDAD_ORGANICA_FOLIO: str | None = None


class CredencialRequest(BaseModel):
    sistema: str
    usuario: str
    password: str


class CredencialResponse(BaseModel):
    sistema: str
    usuario: str


class LicenciaEstado(BaseModel):
    valida: bool
    usuario: str
    mensaje: str


class GuardarLicenciaRequest(BaseModel):
    clave: str


class LicenciaResultado(BaseModel):
    ok: bool
    mensaje: str
