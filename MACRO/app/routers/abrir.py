"""Router para abrir carpeta / archivo MACRO del caso (lado servidor = PC del usuario)."""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from MACRO.app.schemas.abrir import AbrirCasoRequest, AbrirResponse

router = APIRouter(prefix="/api/abrir", tags=["abrir"])


def _carpeta(row: dict, archivo: bool) -> str:
    from MACRO.funciones.funciones_casos import get_archive_folder, get_case_folder

    return get_archive_folder(row) if archivo else get_case_folder(row)


@router.post("/carpeta", response_model=AbrirResponse)
def abrir_carpeta(body: AbrirCasoRequest) -> AbrirResponse:
    """Abre la carpeta del caso (de descargas o de archivo) en el explorador."""
    from MACRO.funciones.funciones_casos import abrir_en_sistema

    folder = _carpeta(body.row, body.archivo)
    if not folder or not os.path.isdir(folder):
        raise HTTPException(status_code=404, detail=f"La carpeta del caso no existe: {folder}")
    abrir_en_sistema(folder)
    return AbrirResponse(ok=True, path=folder)


@router.post("/macro", response_model=AbrirResponse)
def abrir_macro(body: AbrirCasoRequest) -> AbrirResponse:
    """Abre el archivo MACRO.xlsx del caso (de descargas o de archivo)."""
    from MACRO.funciones.funciones_casos import abrir_en_sistema

    cod_tip_sol = str(body.row.get("cod_tip_sol", "") or body.row.get("cod_sol", ""))
    if cod_tip_sol == "12":
        raise HTTPException(status_code=400, detail="La solicitud tipo 12 no genera MACRO.xlsx")

    file_path = os.path.join(_carpeta(body.row, body.archivo), "MACRO.xlsx")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"No existe el archivo: {file_path}")
    abrir_en_sistema(file_path)
    return AbrirResponse(ok=True, path=file_path)
