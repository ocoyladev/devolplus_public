"""Router de configuración: rutas y credenciales (sin exponer contraseñas)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel

from MACRO.app.schemas.config import (
    CredencialRequest,
    CredencialResponse,
    RutasConfig,
)

router = APIRouter(prefix="/api/config", tags=["config"])

RUTAS_KEYS = [
    "PATH_DESCARGAS",
    "PATH_RI",
    "PATH_AUTORIZAR",
    "PATH_ARCHIVO",
    "PATH_SIRAT_EXE",
    "UNIDAD_ORGANICA_FOLIO",
]


def _defaults() -> dict[str, str]:
    # Valores por defecto idénticos a la GUI Flet (config.py).
    from MACRO.config import (
        DEFAULT_PATH_ARCHIVO,
        DEFAULT_PATH_AUTORIZAR,
        DEFAULT_PATH_DESCARGAS,
        DEFAULT_PATH_RI,
        DEFAULT_PATH_SIRAT_EXE,
    )

    return {
        "PATH_DESCARGAS": DEFAULT_PATH_DESCARGAS,
        "PATH_RI": DEFAULT_PATH_RI,
        "PATH_AUTORIZAR": DEFAULT_PATH_AUTORIZAR,
        "PATH_ARCHIVO": DEFAULT_PATH_ARCHIVO,
        "PATH_SIRAT_EXE": DEFAULT_PATH_SIRAT_EXE,
        "UNIDAD_ORGANICA_FOLIO": "7EC400",
    }


def _leer_rutas() -> RutasConfig:
    from MACRO.database import obtener_config

    defaults = _defaults()
    return RutasConfig(
        **{k: obtener_config(k, defaults.get(k)) for k in RUTAS_KEYS}
    )


class SeleccionCarpetaResponse(BaseModel):
    ruta: str


@router.get("/rutas", response_model=RutasConfig)
def get_rutas() -> RutasConfig:
    return _leer_rutas()


@router.put("/rutas", response_model=RutasConfig)
def put_rutas(body: RutasConfig) -> RutasConfig:
    from MACRO.database import guardar_config

    for clave, valor in body.model_dump(exclude_none=True).items():
        guardar_config(clave, valor)
    return _leer_rutas()


@router.get("/credenciales/{sistema}", response_model=CredencialResponse)
def get_credenciales(sistema: str) -> CredencialResponse:
    from MACRO.database import obtener_credenciales

    creds = obtener_credenciales(sistema, incluir_password=False) or {}
    return CredencialResponse(sistema=sistema, usuario=creds.get("usuario", ""))


@router.put("/credenciales", response_model=CredencialResponse)
def put_credenciales(body: CredencialRequest) -> CredencialResponse:
    from MACRO.database import guardar_credenciales

    # El usuario de Portal debe guardarse SIEMPRE en mayúsculas (el sistema
    # lo exige; en minúsculas falla).
    usuario = (
        body.usuario.upper()
        if body.sistema.strip().lower() == "portal"
        else body.usuario
    )
    guardar_credenciales(body.sistema, usuario, body.password)
    return CredencialResponse(sistema=body.sistema, usuario=usuario)


@router.post("/seleccionar-carpeta", response_model=SeleccionCarpetaResponse)
def seleccionar_carpeta_endpoint() -> SeleccionCarpetaResponse:
    """Abre el diálogo nativo de selección de carpeta y devuelve la ruta elegida.

    Se ejecuta en un hilo NUEVO para garantizar un apartment COM (STA) limpio:
    los hilos reutilizados del threadpool de FastAPI pueden estar inicializados en
    otro modo, lo que hacía que SHGetPathFromIDListW devolviera una ruta vacía.
    """
    # 1) Preferir el diálogo nativo de pywebview: corre en el hilo GUI de WebView2
    #    y devuelve la ruta de forma fiable (el diálogo ctypes desde un hilo del
    #    servidor a veces devolvía vacío).
    try:
        import webview

        from MACRO.app import launcher

        win = getattr(launcher, "WINDOW", None)
        if win is not None:
            res = win.create_file_dialog(webview.FOLDER_DIALOG)
            if res:
                ruta = res[0] if isinstance(res, (list, tuple)) else res
                return SeleccionCarpetaResponse(ruta=str(ruta or ""))
            return SeleccionCarpetaResponse(ruta="")
    except Exception:  # noqa: BLE001 — si falla, caemos al método ctypes
        pass

    # 2) Fallback (modo navegador o si pywebview no está disponible): diálogo
    #    nativo por ctypes en un hilo nuevo (apartment COM limpio).
    import threading

    from MACRO.funciones.funciones_generales import seleccionar_carpeta

    resultado: dict[str, str] = {"ruta": ""}

    def _abrir() -> None:
        try:
            resultado["ruta"] = seleccionar_carpeta("Seleccione la carpeta") or ""
        except Exception:  # noqa: BLE001 — si falla, queda vacío
            resultado["ruta"] = ""

    hilo = threading.Thread(target=_abrir)
    hilo.start()
    hilo.join()
    return SeleccionCarpetaResponse(ruta=resultado["ruta"])


class FeriadosResponse(BaseModel):
    feriados: list[str]  # DD/MM/YYYY


class FeriadoRequest(BaseModel):
    fecha: str  # DD/MM/YYYY


def _leer_feriados() -> FeriadosResponse:
    from MACRO.database import obtener_feriados

    out: list[str] = []
    for f in obtener_feriados():
        try:
            out.append(datetime.strptime(str(f), "%Y-%m-%d").strftime("%d/%m/%Y"))
        except ValueError:
            out.append(str(f))
    return FeriadosResponse(feriados=out)


def _a_ymd(fecha: str) -> str:
    try:
        return datetime.strptime(fecha.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Fecha inválida (use DD/MM/YYYY)") from exc


@router.get("/feriados", response_model=FeriadosResponse)
def get_feriados() -> FeriadosResponse:
    return _leer_feriados()


@router.post("/feriados", response_model=FeriadosResponse)
def add_feriado(body: FeriadoRequest) -> FeriadosResponse:
    from MACRO.database import agregar_feriado

    agregar_feriado(_a_ymd(body.fecha))
    return _leer_feriados()


@router.post("/feriados/eliminar", response_model=FeriadosResponse)
def del_feriado(body: FeriadoRequest) -> FeriadosResponse:
    from MACRO.database import eliminar_feriado

    eliminar_feriado(_a_ymd(body.fecha))
    return _leer_feriados()
