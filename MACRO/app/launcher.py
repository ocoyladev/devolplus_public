"""Lanzador de la app web de DEVOL+: servidor local + ventana WebView2."""
from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn

from MACRO.app.runtime import (
    configurar_log_consola,
    ensure_std_streams,
    uvicorn_log_config,
)
from MACRO.app.server import create_app

HOST = "127.0.0.1"

# Ventana pywebview activa (la usa el endpoint de selección de carpeta para
# abrir el diálogo nativo en el hilo GUI, que es lo fiable en WebView2).
WINDOW = None


def pick_free_port(start: int = 8080, host: str = HOST) -> int:
    """Devuelve el primer puerto libre >= ``start`` en ``host``."""
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
    """Carpeta del frontend compilado, tanto congelado (PyInstaller) como en dev."""
    if getattr(sys, "frozen", False):  # empaquetado con PyInstaller
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base / "frontend" / "dist"
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


def run_server(port: int) -> None:
    """Ejecuta uvicorn (bloqueante). Pensado para correr en un hilo."""
    ensure_std_streams()
    configurar_log_consola()  # todo lo de consola -> devolplus_consola.log
    app = create_app(static_dir=resolve_static_dir())
    uvicorn.run(app, host=HOST, port=port, log_config=uvicorn_log_config("devolplus.log"))


def open_window(port: int) -> None:
    """Abre la ventana WebView2 apuntando al servidor local.

    Importa ``webview`` de forma diferida para no exigir backend GUI en tests.
    """
    import webview  # noqa: PLC0415  (import diferido intencional)

    global WINDOW
    WINDOW = webview.create_window(
        "DEVOL+", f"http://{HOST}:{port}", width=1280, height=800
    )
    webview.start()


def main() -> None:
    port = pick_free_port(start=8080)
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()
    # Pequeña espera para que uvicorn levante antes de abrir la ventana.
    time.sleep(1.0)
    open_window(port)


if __name__ == "__main__":
    main()
