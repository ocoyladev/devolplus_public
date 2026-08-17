"""Gestor de jobs en background.

Ejecuta trabajo bloqueante (descargas ``requests``, Excel COM, pandas) en hilos
y reporta progreso mediante una función ``emit`` thread-safe (inyectada). El
servidor conecta ``emit`` al difusor WebSocket; las pruebas inyectan un colector.
"""
from __future__ import annotations

import threading
import traceback
import uuid
from typing import Callable

# Una tarea recibe un callback de progreso ``progreso(mensaje: str)`` y puede
# devolver cualquier cosa (se ignora el valor; el resultado se comunica por WS).
Tarea = Callable[[Callable[[str], None]], object]
Emit = Callable[[dict], None]


class JobManager:
    def __init__(self, emit: Emit) -> None:
        self._emit = emit
        self._threads: dict[str, threading.Thread] = {}

    def _progreso(self, job_id: str, kind: str, num_doc: str | None):
        """Callback que traduce un mensaje de flujo a un evento ``progress``."""
        def progreso(mensaje) -> None:
            ev = {"type": "progress", "job_id": job_id, "kind": kind, "num_doc": num_doc}
            if isinstance(mensaje, dict):
                for k in ("done", "total", "etiqueta", "msg"):
                    if k in mensaje:
                        ev[k] = mensaje[k]
            else:
                ev["msg"] = str(mensaje)
            self._emit(ev)
        return progreso

    def callback_sincrono(self, *, kind: str):
        """Callback de progreso para trabajo que NO es un job.

        'Validar archivo' responde en la misma petición (el resultado es la
        respuesta, no un evento), pero puede tardar bastante sobre muchos casos.
        Emite los mismos eventos ``progress`` para que la UI muestre el avance;
        al no haber job, nunca llega un ``job_done``, así que el consumidor debe
        dejar de mostrarlos cuando la petición termina.
        """
        return self._progreso("", kind, None)

    def run(self, tarea: Tarea, *, kind: str = "task", num_doc: str | None = None) -> str:
        """Lanza ``tarea`` en un hilo daemon y devuelve su ``job_id``.

        Emite eventos ``progress`` por cada llamada al callback y un único
        ``job_done`` al terminar (con ``ok``/``error``).
        """
        job_id = str(uuid.uuid4())
        progreso = self._progreso(job_id, kind, num_doc)

        def worker() -> None:
            try:
                resultado = tarea(progreso)
                # Los flujos devuelven {'exito': bool, 'mensaje': str}. Si 'exito'
                # es False NO es una excepción, pero debe reportarse como fallo.
                if isinstance(resultado, dict) and resultado.get("exito") is False:
                    evento_fallo = {
                        "type": "job_done",
                        "job_id": job_id,
                        "kind": kind,
                        "num_doc": num_doc,
                        "ok": False,
                        "error": str(resultado.get("mensaje", "El proceso falló")),
                    }
                    # Detalle estructurado de casos con error (p. ej. Generar PPTT).
                    if resultado.get("errores"):
                        evento_fallo["errores"] = list(resultado["errores"])
                    if "ok_count" in resultado:
                        evento_fallo["ok_count"] = resultado["ok_count"]
                    if isinstance(resultado.get("detalle"), (list, tuple)):
                        evento_fallo["detalle"] = list(resultado["detalle"])
                    for _clave in ("oks", "ya_descargadas", "omitidos"):
                        if isinstance(resultado.get(_clave), (list, tuple)):
                            evento_fallo[_clave] = list(resultado[_clave])
                    self._emit(evento_fallo)
                else:
                    evento = {
                        "type": "job_done",
                        "job_id": job_id,
                        "kind": kind,
                        "num_doc": num_doc,
                        "ok": True,
                        "mensaje": (
                            resultado.get("mensaje")
                            if isinstance(resultado, dict)
                            else None
                        ),
                    }
                    # Casos preexistentes en archivo (omitidos): el front ofrece
                    # desarchivarlos. Solo es una lista (viene de "Cargar datos");
                    # otros flujos usan claves distintas para sus conteos, así que
                    # se ignora cualquier valor que no sea lista/tupla.
                    if isinstance(resultado, dict) and isinstance(
                        resultado.get("archivados"), (list, tuple)
                    ) and resultado["archivados"]:
                        evento["archivados"] = list(resultado["archivados"])
                    # Detalle estructurado de casos con error y conteo OK (Generar PPTT):
                    # el proceso puede terminar con éxito parcial (algunos casos fallan).
                    if isinstance(resultado, dict) and resultado.get("errores"):
                        evento["errores"] = list(resultado["errores"])
                    if isinstance(resultado, dict) and "ok_count" in resultado:
                        evento["ok_count"] = resultado["ok_count"]
                    for _clave in ("oks", "ya_descargadas", "omitidos"):
                        if isinstance(resultado, dict) and isinstance(
                            resultado.get(_clave), (list, tuple)
                        ):
                            evento[_clave] = list(resultado[_clave])
                    # Detalle por echasqui (Archivar ECHASQUI): alimenta el modal de resumen.
                    if isinstance(resultado, dict) and isinstance(
                        resultado.get("detalle"), (list, tuple)
                    ):
                        evento["detalle"] = list(resultado["detalle"])
                    self._emit(evento)
            except Exception as exc:  # noqa: BLE001 — se reporta al cliente
                # Traceback completo al log de consola (devolplus_consola.log).
                print(f"[job:{kind}] ERROR: {exc}")
                traceback.print_exc()
                self._emit(
                    {
                        "type": "job_done",
                        "job_id": job_id,
                        "kind": kind,
                        "num_doc": num_doc,
                        "ok": False,
                        "error": str(exc),
                    }
                )

        thread = threading.Thread(target=worker, daemon=True)
        self._threads[job_id] = thread
        thread.start()
        return job_id

    def join(self, job_id: str, timeout: float | None = None) -> None:
        """Espera a que un job termine. Pensado para pruebas."""
        thread = self._threads.get(job_id)
        if thread is not None:
            thread.join(timeout)
