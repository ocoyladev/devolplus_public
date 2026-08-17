"""Factory de la app FastAPI de DEVOL+ (capa web delgada)."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from MACRO.app.jobs import JobManager
from MACRO.app.websocket import ConnectionManager


def create_app(static_dir: Path | None = None) -> FastAPI:
    """Construye la app FastAPI.

    Args:
        static_dir: carpeta con el frontend compilado (``frontend/dist``).
            Si es ``None`` o no existe, no se monta estático (útil en tests).
    """
    manager = ConnectionManager()

    # ``emit`` reenvía eventos desde hilos worker al loop asyncio para difundir
    # por WebSocket. El loop se captura en el startup (lifespan); hasta entonces
    # los eventos se descartan (no hay clientes conectados todavía).
    state: dict[str, asyncio.AbstractEventLoop | None] = {"loop": None}

    def emit(message: dict) -> None:
        loop = state["loop"]
        if loop is not None:
            asyncio.run_coroutine_threadsafe(manager.broadcast(message), loop)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Crea las tablas si no existen (credenciales, tabla_asign, configuracion…),
        # igual que hace la GUI Flet al iniciar.
        try:
            from MACRO.database import init_db

            init_db()
        except Exception:  # noqa: BLE001 — no debe impedir el arranque del servidor
            pass
        # Tablas locales de caché/cola del control de acceso (tolerancia a
        # caídas de Oracle). Idempotente; no debe frenar el arranque.
        try:
            from MACRO.auth.cache_local import ensure_tablas_auth

            ensure_tablas_auth()
        except Exception:  # noqa: BLE001
            pass
        state["loop"] = asyncio.get_running_loop()
        yield

    app = FastAPI(title="DEVOL+", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.state.connection_manager = manager
    app.state.jobs = JobManager(emit)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/version")
    def version() -> dict[str, str]:
        # La versión la resuelve el backend (archivo VERSION embebido por la
        # spec); el frontend la consulta en runtime, así el dist no depende de
        # con qué versión se empaquetó el .exe.
        from MACRO.version import get_version

        return {"version": get_version()}

    @app.websocket("/ws")
    async def ws(socket: WebSocket) -> None:
        await manager.connect(socket)
        try:
            while True:
                msg = await socket.receive_json()
                if msg.get("type") == "ping":
                    await socket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            manager.disconnect(socket)

    # Routers de features (capa delgada sobre flujos/funciones). Se registran
    # antes del fallback SPA para que /api/* tenga prioridad.
    from MACRO.app.routers import (
        abrir,
        acceso,
        campos,
        cartas,
        config,
        datos,
        descargas,
        entorno,
        generar,
        mesa_ayuda,
        mantenimiento,
        procesos,
        servicios,
        sync,
    )

    app.include_router(campos.router)
    app.include_router(datos.router)
    app.include_router(descargas.router)
    app.include_router(abrir.router)
    app.include_router(procesos.router)
    app.include_router(config.router)
    app.include_router(acceso.router)
    app.include_router(servicios.router)
    app.include_router(mesa_ayuda.router)
    app.include_router(generar.router)
    app.include_router(sync.router)
    app.include_router(mantenimiento.router)
    app.include_router(entorno.router)
    app.include_router(cartas.router)

    if static_dir is not None and static_dir.is_dir():
        index = static_dir / "index.html"
        assets = static_dir / "assets"

        # Archivos reales generados por Vite (JS/CSS con hash) bajo /assets.
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        # Manual de usuario (HTML autocontenido + capturas). Se monta antes del
        # fallback SPA para que /manual/ sirva la guía y no el index de la app.
        manual = static_dir / "manual"
        if manual.is_dir():
            app.mount("/manual", StaticFiles(directory=manual, html=True), name="manual")

        @app.get("/")
        def root() -> FileResponse:
            return FileResponse(index)

        # SPA fallback: cualquier ruta no-API devuelve index.html. Se registra
        # después de /api/* y /, así que esas rutas explícitas tienen prioridad.
        @app.get("/{full_path:path}")
        def spa(full_path: str) -> FileResponse:
            return FileResponse(index)

    return app
