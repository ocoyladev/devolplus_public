"""Utilidades de arranque compartidas por los lanzadores (app y admin).

Centraliza dos cosas necesarias cuando el ``.exe`` se empaqueta con
``console=False`` (modo *windowed* de PyInstaller):

* ``ensure_std_streams``: garantiza ``sys.stdout``/``sys.stderr`` no nulos.
* ``uvicorn_log_config``: manda los logs de uvicorn a un archivo rotativo junto
  al ejecutable, para poder diagnosticar releases sin volver a ``console=True``.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path


def ensure_std_streams() -> None:
    """Garantiza ``sys.stdout``/``sys.stderr`` no nulos.

    En el ``.exe`` con ``console=False`` ambos valen ``None``; uvicorn falla al
    construir su logger (``DefaultFormatter`` llama a ``sys.stdout.isatty()``),
    el hilo del servidor muere antes de abrir el puerto y la ventana muestra
    "se rechazó la conexión". Se redirigen a ``os.devnull`` como red de
    seguridad para cualquier código que escriba a esos streams.
    """
    for _name in ("stdout", "stderr"):
        if getattr(sys, _name, None) is None:
            setattr(sys, _name, open(os.devnull, "w", encoding="utf-8"))


def log_dir() -> Path:
    """Carpeta donde dejar los logs: junto al ``.exe`` (frozen) o el cwd (dev)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path.cwd()


class _Tee:
    """Escribe en varios streams a la vez (consola + archivo). Robusto: si un
    stream falla, no interrumpe la escritura en los demás."""

    def __init__(self, *streams) -> None:
        self._streams = [s for s in streams if s is not None]

    def write(self, data) -> int:
        for s in self._streams:
            try:
                s.write(data)
                s.flush()
            except Exception:  # noqa: BLE001 — el logging nunca debe romper el flujo
                pass
        return len(data)

    def flush(self) -> None:
        for s in self._streams:
            try:
                s.flush()
            except Exception:  # noqa: BLE001
                pass

    def isatty(self) -> bool:
        return False


def configurar_log_consola(nombre_archivo: str = "devolplus_consola.log") -> None:
    """Redirige ``stdout``/``stderr`` a un *tee* consola+archivo, para que todo lo
    que antes se veía en consola (prints, tracebacks, mensajes de error de las
    distintas funciones) quede registrado en un archivo junto al ejecutable.

    Rotación simple: si el archivo supera ~2 MB, se respalda como ``.1``. Nunca
    lanza: si no puede abrir el archivo, deja los streams como están."""
    ruta = log_dir() / nombre_archivo
    try:
        if ruta.exists() and ruta.stat().st_size > 2_000_000:
            respaldo = ruta.with_suffix(ruta.suffix + ".1")
            try:
                respaldo.unlink()
            except FileNotFoundError:
                pass
            ruta.rename(respaldo)
        f = open(ruta, "a", encoding="utf-8", buffering=1)
    except Exception:  # noqa: BLE001 — no romper el arranque por el log
        return
    f.write(f"\n===== Sesión iniciada {datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
    base_out = getattr(sys, "stdout", None)
    base_err = getattr(sys, "stderr", None)
    sys.stdout = _Tee(base_out, f)
    sys.stderr = _Tee(base_err, f)


def uvicorn_log_config(nombre_archivo: str) -> dict:
    """``dictConfig`` de uvicorn que escribe a un archivo rotativo.

    Usa un ``RotatingFileHandler`` (1 MB × 3 backups) en vez de la consola, así
    que además evita el crash de ``console=False``: no depende de
    ``DefaultFormatter``/``isatty`` ni de ``sys.stdout``.
    """
    ruta = log_dir() / nombre_archivo
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "archivo": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "archivo": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(ruta),
                "maxBytes": 1_000_000,
                "backupCount": 3,
                "encoding": "utf-8",
                "formatter": "archivo",
            }
        },
        "loggers": {
            "uvicorn": {"handlers": ["archivo"], "level": "INFO", "propagate": False},
            "uvicorn.error": {
                "handlers": ["archivo"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["archivo"],
                "level": "WARNING",
                "propagate": False,
            },
        },
    }
