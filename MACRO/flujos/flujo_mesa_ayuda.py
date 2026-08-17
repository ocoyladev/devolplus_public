"""Registro de tickets en el sistema de mesa de ayuda (modo demostración).

Toda la lógica de armado y validación de los tickets es real (vive en
:mod:`MACRO.mesa_ayuda.tickets`); lo único que sustituye el modo demo es el envío:
:func:`registrar_ticket` no hace ninguna llamada remota y devuelve un
identificador simulado.
"""

from __future__ import annotations

from datetime import date

from MACRO.mesa_ayuda import periodos, tickets
from MACRO.mesa_ayuda.tickets import DatosModificar, DatosTicket, requiere_cci

# Tipos de ticket de descarga admitidos.
TIPOS_DESCARGA: tuple[str, ...] = ("4ta", "5ta", "601", "601_completo")


def _of(row: dict) -> str:
    return str((row or {}).get("of_devolucion") or (row or {}).get("of") or "").strip()


def _ruc(row: dict) -> str:
    """RUC del caso, tolerando los distintos nombres de columna."""
    for c in ("num_ruc", "ruc", "N° RUC"):
        valor = str((row or {}).get(c, "")).strip()
        if valor:
            return valor
    return ""


def _nombre(row: dict) -> str:
    for c in ("ddp_nombre", "nombre", "NOMBRE"):
        valor = str((row or {}).get(c, "")).strip()
        if valor:
            return valor
    return ""


def _per_doc(row: dict) -> str:
    """Periodo del documento en formato ``YYYYMM`` / ``YYYY13``."""
    return str((row or {}).get("per_doc", "")).strip()


def _num_doc(row: dict) -> str:
    return str((row or {}).get("num_doc", "")).strip()


def necesita_cci(modalidad: str) -> bool:
    """Reexporta la regla de negocio de :mod:`MACRO.mesa_ayuda.tickets`."""
    return requiere_cci(modalidad)


def datos_descarga_desde_fila(
    tipo: str,
    row: dict,
    *,
    ruc_empleador: str | None = None,
    nombre_empleador: str | None = None,
    doc_override: str | None = None,
) -> DatosTicket:
    """Arma un ``DatosTicket`` (4ta/5ta/601) a partir de una fila del caso."""
    if tipo not in TIPOS_DESCARGA:
        raise ValueError(
            f"Tipo de descarga inválido: {tipo!r} (use {', '.join(TIPOS_DESCARGA)})")
    ejercicio = periodos.ejercicio_de_per_doc(_per_doc(row))
    if tipo in ("601", "601_completo") and not (ruc_empleador and nombre_empleador):
        raise ValueError("601 requiere RUC y nombre del empleador")
    return DatosTicket(
        tipo=tipo,
        of=_of(row),
        ruc=_ruc(row),
        nombre=_nombre(row),
        ejercicio=ejercicio,
        ruc_empleador=(ruc_empleador.strip() if ruc_empleador else None),
        nombre_empleador=(nombre_empleador.strip() if nombre_empleador else None),
        doc_override=(doc_override.strip() if doc_override else None),
    )


def datos_modificar_desde_fila(
    row: dict, modalidad: str, cci: str | None = None,
) -> DatosModificar:
    """Arma un ``DatosModificar`` usando el ``num_doc`` de la fila como nro. orden."""
    if modalidad not in tickets.MODALIDADES:
        raise ValueError(f"Modalidad inválida: {modalidad!r}")
    cci = cci.strip() if cci else None
    if necesita_cci(modalidad) and not cci:
        raise ValueError("La modalidad 'De Cheque a Abono en Cuenta' requiere CCI")
    return DatosModificar(
        modalidad=modalidad, ruc=_ruc(row), nro_orden=_num_doc(row), cci=cci)


def resumen(datos, hoy: date | None = None) -> str:
    """Texto de resumen para el diálogo de confirmación previo al envío."""
    if isinstance(datos, DatosModificar):
        lineas = [
            f"Modalidad: {datos.modalidad.strip()}",
            f"RUC: {datos.ruc}",
            f"N° de orden: {datos.nro_orden}",
        ]
        if datos.cci:
            lineas.append(f"CCI: {datos.cci}")
        return "\n".join(lineas)
    return "\n".join([
        f"Título: {tickets.titulo(datos)}",
        f"Descripción: {tickets.descripcion(datos, hoy)}",
        f"Contenido: {tickets.contenido_txt(datos, hoy)}",
    ])


def extraer_empleadores_601(ruta: str) -> list[dict]:
    """Lee el reporte de empleadores. En demo devuelve un conjunto sintético fijo.

    Los RUC son sintéticos y no corresponden a ninguna empresa registrada.
    """
    del ruta
    return [
        {"ruc_empleador": "20100000001", "nombre_empleador": "COMERCIAL DEMO SAC"},
        {"ruc_empleador": "20100000002", "nombre_empleador": "SERVICIOS DEMO EIRL"},
    ]


def registrar_ticket(datos, *, cliente=None, hoy: date | None = None) -> dict:
    """Registra el ticket. En demo no hay llamada remota: devuelve un id simulado."""
    del cliente
    referencia = getattr(datos, "nro_orden", None) or getattr(datos, "of", "")
    return {
        "ok": True,
        "ticket_id": f"DEMO-{referencia or '000'}",
        "titulo": (
            None if isinstance(datos, DatosModificar) else tickets.titulo(datos)
        ),
        "mensaje": "Ticket registrado (demo)",
    }


__all__ = [
    "TIPOS_DESCARGA", "datos_descarga_desde_fila", "datos_modificar_desde_fila",
    "extraer_empleadores_601", "registrar_ticket", "necesita_cci", "resumen",
]
