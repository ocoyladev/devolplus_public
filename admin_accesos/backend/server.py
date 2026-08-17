"""Factory de la app FastAPI de administración de accesos."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

EstadoDecision = Literal["aprobado", "rechazado", "inactivo", "pendiente"]


class DecisionRequest(BaseModel):
    estado: EstadoDecision
    observaciones: str | None = None


class ResultadoResponse(BaseModel):
    ok: bool
    mensaje: str


def create_app(static_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="DEVOL+ · Admin de accesos", docs_url=None, redoc_url=None)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/version")
    def version() -> dict[str, str]:
        from MACRO.version import get_version

        return {"version": get_version()}

    @app.get("/api/solicitudes")
    def solicitudes(estado: str | None = None) -> list[dict[str, Any]]:
        from MACRO.auth.admin_service import listar_solicitudes

        try:
            return listar_solicitudes(estado)
        except Exception as exc:  # noqa: BLE001 — reporta fallo de BD como 503
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.patch("/api/solicitudes/{usuario_id}", response_model=ResultadoResponse)
    def decidir(usuario_id: int, body: DecisionRequest) -> ResultadoResponse:
        from MACRO.auth.admin_service import actualizar_estado
        from MACRO.auth.auth_service import obtener_usuario_red

        try:
            r = actualizar_estado(
                usuario_id=usuario_id,
                nuevo_estado=body.estado,
                admin_actual=obtener_usuario_red(),
                observaciones=body.observaciones,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return ResultadoResponse(ok=r["ok"], mensaje=r["mensaje"])

    @app.get("/api/logueos")
    def logueos(usuario_red: str | None = None, limite: int = 50) -> list[dict[str, Any]]:
        from MACRO.auth.admin_service import historial_logueos

        try:
            return historial_logueos(usuario_red, limite)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    if static_dir is not None and static_dir.is_dir():
        index = static_dir / "index.html"
        assets = static_dir / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/")
        def root() -> FileResponse:
            return FileResponse(index)

        @app.get("/{full_path:path}")
        def spa(full_path: str) -> FileResponse:
            return FileResponse(index)

    return app
