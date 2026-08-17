"""Abort por hotkey (Ctrl+Shift+Q) para las automatizaciones de escritorio.

El FAILSAFE de pyautogui (mover el mouse a una esquina) no dispara de forma
fiable con pantalla extendida, así que este módulo ofrece un abort por teclado
que no depende de la posición del cursor.

Un hilo daemon consulta el estado FÍSICO del teclado con ``GetAsyncKeyState``
(Win32) cada ``INTERVALO_POLL`` segundos y ENGANCHA un ``threading.Event`` en
cuanto ve la combinación. Gracias al latch basta un toque: la parada real ocurre
en el siguiente ``verificar()`` del flujo, sin tener que sostener las teclas
esperando a que la automatización llegue a un punto de chequeo.

``Ctrl+Shift+Q`` es seguro frente a la propia automatización: pyautogui sintetiza
``ctrl+v/p/a/s/w/f4`` y ``alt+tab/-/a``, y Shift solo aparece dentro de
``typewrite`` (mayúsculas de rutas y de la clave), nunca junto a Ctrl. Es decir,
el script no puede auto-abortarse.

Fuera de Windows todo degrada a no-op, para que la suite corra en Linux.
"""
from __future__ import annotations

import threading
from typing import Callable

# Virtual-Key codes de Win32 (winuser.h).
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_Q = 0x51
# GetAsyncKeyState marca "pulsada ahora mismo" en el bit más significativo.
_BIT_PRESIONADA = 0x8000

INTERVALO_POLL = 0.05
COMBINACION = "Ctrl+Shift+Q"
MENSAJE_ABORTO = f"⛔ Abortado por el usuario ({COMBINACION}) — deteniendo…"


class AbortadoPorUsuario(RuntimeError):
    """El usuario pidió abortar con el hotkey.

    Debe atravesar los ``except Exception`` genéricos de los bucles por-caso: no
    es el fallo de un caso, es una orden de parar todo el lote.
    """


_detectado = threading.Event()
_parar = threading.Event()
_hilo: threading.Thread | None = None
_lock = threading.Lock()


def _leer_estado_win32(vk: int) -> int:
    """Estado físico de la tecla ``vk``. Devuelve 0 si no estamos en Windows."""
    try:
        import ctypes  # noqa: PLC0415

        return ctypes.windll.user32.GetAsyncKeyState(vk)
    except Exception:  # noqa: BLE001 - no-Windows o API no disponible
        return 0


def _combinacion_presionada(leer_estado: Callable[[int], int]) -> bool:
    """True si Ctrl, Shift y Q están pulsadas a la vez."""
    return all(
        leer_estado(vk) & _BIT_PRESIONADA
        for vk in (VK_CONTROL, VK_SHIFT, VK_Q)
    )


def _vigilar(leer_estado: Callable[[int], int],
            on_detect: Callable[[str], None] | None) -> None:
    """Bucle del hilo daemon: engancha el flag y avisa UNA sola vez."""
    while not _parar.wait(INTERVALO_POLL):
        try:
            if not _combinacion_presionada(leer_estado):
                continue
        except Exception:  # noqa: BLE001 - nunca tumbar el hilo por el lector
            continue
        if _detectado.is_set():
            continue
        _detectado.set()
        if on_detect is not None:
            try:
                on_detect(MENSAJE_ABORTO)
            except Exception:  # noqa: BLE001 - el log no debe romper el abort
                pass


def activar(on_detect: Callable[[str], None] | None = None,
            _leer_estado: Callable[[int], int] | None = None) -> None:
    """Arma el vigilante. Limpia cualquier estado de una corrida anterior.

    ``on_detect`` recibe ``MENSAJE_ABORTO`` en cuanto se detecta la combinación,
    para pintarlo en el log en vivo aunque la parada efectiva ocurra en el
    chequeo siguiente. ``_leer_estado`` existe solo para los tests.
    """
    desactivar()
    leer = _leer_estado or _leer_estado_win32
    with _lock:
        global _hilo
        _detectado.clear()
        _parar.clear()
        _hilo = threading.Thread(
            target=_vigilar, args=(leer, on_detect),
            name="abort-hotkey", daemon=True,
        )
        _hilo.start()


def desactivar() -> None:
    """Detiene el vigilante y limpia el latch. Idempotente; usar en un finally."""
    with _lock:
        global _hilo
        _parar.set()
        hilo, _hilo = _hilo, None
    if hilo is not None:
        hilo.join(timeout=1.0)
    _detectado.clear()


def abortado() -> bool:
    """True si el usuario ya pulsó la combinación en esta corrida."""
    return _detectado.is_set()


def verificar() -> None:
    """Punto de chequeo: lanza ``AbortadoPorUsuario`` si el latch está enganchado."""
    if _detectado.is_set():
        raise AbortadoPorUsuario(MENSAJE_ABORTO)


def esperar_deteccion(timeout: float) -> bool:
    """Bloquea hasta ``timeout`` esperando la detección. Solo para tests."""
    return _detectado.wait(timeout)


def es_abort(exc: BaseException) -> bool:
    """True si ``exc`` es el abort del usuario (para re-lanzarlo en los except)."""
    return isinstance(exc, AbortadoPorUsuario)
