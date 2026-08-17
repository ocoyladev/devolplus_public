"""Lanzador del admin de accesos: servidor local + ventana WebView2.

Se ejecuta desde la raíz del repo (``python -m admin_accesos.backend.main``) para
que el paquete ``MACRO`` sea importable.
"""
from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn

from admin_accesos.backend.server import create_app
from MACRO.app.runtime import ensure_std_streams, uvicorn_log_config

HOST = "127.0.0.1"


def pick_free_port(start: int = 8090, host: str = HOST) -> int:
    for port in range(start, 65536):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError("No hay puertos libres disponibles")


def resolve_static_dir() -> Path:
    if getattr(sys, "frozen", False):  # empaquetado con PyInstaller
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base / "frontend" / "dist"
    return Path(__file__).resolve().parents[1] / "frontend" / "dist"


def run_server(port: int) -> None:
    ensure_std_streams()
    app = create_app(static_dir=resolve_static_dir())
    uvicorn.run(
        app, host=HOST, port=port, log_config=uvicorn_log_config("devolplus_admin.log")
    )


def open_window(port: int) -> None:
    import webview  # noqa: PLC0415 (import diferido intencional)

    webview.create_window(
        "DEVOL+ · Admin de accesos",
        f"http://{HOST}:{port}",
        width=1200,
        height=780,
    )
    webview.start()


def main() -> None:
    port = pick_free_port(start=8090)
    threading.Thread(target=run_server, args=(port,), daemon=True).start()
    time.sleep(1.0)
    open_window(port)


if __name__ == "__main__":
    main()
