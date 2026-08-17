"""Derivación de periodos y del documento del trabajador para los tickets Mesa de Ayuda.

Lógica pura, sin dependencias de red ni de la base de datos. Los periodos se
manejan como enteros en formato ``YYYYMM``.
"""

from __future__ import annotations

from datetime import date


def ejercicio_de_per_doc(per_doc: str | int) -> int:
    """Devuelve el ejercicio (año) a partir de los primeros 4 dígitos de per_doc.

    Ej.: ``"202513"`` -> ``2025``. Lanza ``ValueError`` si no hay 4 dígitos.
    """
    s = str(per_doc).strip()
    if len(s) < 4 or not s[:4].isdigit():
        raise ValueError(f"per_doc inválido: {per_doc!r} (se esperan 4 dígitos de año)")
    return int(s[:4])


def mes_concluido_actual(hoy: date | None = None) -> int:
    """Último mes calendario concluido respecto a ``hoy``, en formato ``YYYYMM``.

    Ej.: hoy = 2026-06-18 -> ``202605``. Para enero, retrocede al diciembre previo.
    """
    if hoy is None:
        hoy = date.today()
    anio, mes = hoy.year, hoy.month - 1
    if mes == 0:
        anio, mes = anio - 1, 12
    return anio * 100 + mes


def periodos_4ta(ejercicio: int, hoy: date | None = None) -> tuple[int, int]:
    """Periodos (inicio, fin) en ``YYYYMM`` para rentas de 4ta.

    Inicio: primer mes del ejercicio previo. Fin: diciembre del ejercicio
    siguiente, pero topado al último mes ya concluido a la fecha.
    """
    inicio = (ejercicio - 1) * 100 + 1
    fin = min((ejercicio + 1) * 100 + 12, mes_concluido_actual(hoy))
    return inicio, fin


def periodos_anuales(ejercicio: int) -> tuple[int, int]:
    """Periodos (inicio, fin) en ``YYYYMM`` para el ejercicio completo (5ta y 601)."""
    return ejercicio * 100 + 1, ejercicio * 100 + 12


def documento_trabajador(ruc: str, override: str | None = None) -> str:
    """Documento de identidad del trabajador a usar en el .txt.

    Si el RUC inicia en ``10`` (persona natural) y tiene 11 dígitos, se toman los
    dígitos del 3.º al 10.º (8 dígitos, el DNI). En cualquier otro caso se usa
    ``override`` (el nro. de identificación suministrado); si no hay override,
    lanza ``ValueError``.
    """
    ruc = str(ruc).strip()
    if ruc.startswith("10") and len(ruc) == 11:
        return ruc[2:10]
    if override:
        return str(override).strip()
    raise ValueError(
        f"El RUC {ruc!r} no inicia en '10'; se requiere el nro. de identificación del trabajador"
    )
