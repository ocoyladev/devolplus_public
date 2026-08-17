"""Definición de los tipos de ticket Mesa de Ayuda y armado de sus textos/archivos.

Cada tipo (4ta / 5ta / 601 / 601_completo) tiene constantes propias (``TicketSpec``) y plantillas
de título, descripción y contenido del ``.txt``. La lógica de periodos y del
documento del trabajador vive en :mod:`MACRO.mesa_ayuda.periodos`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from MACRO.mesa_ayuda import periodos


@dataclass
class DatosTicket:
    """Datos de entrada de un ticket (suministrados por consola en esta versión)."""

    tipo: str  # "4ta" | "5ta" | "601" | "601_completo"
    of: str
    ruc: str
    nombre: str
    ejercicio: int
    # Solo 601:
    ruc_empleador: str | None = None
    nombre_empleador: str | None = None
    # Identificación del trabajador cuando el RUC no inicia en "10":
    doc_override: str | None = None


@dataclass(frozen=True)
class TicketSpec:
    """Constantes del formulario Mesa de Ayuda para un tipo de ticket.

    ``con_adjunto`` distingue los tipos que suben un ``.txt`` (descargas) de los
    que llenan campos de plantilla (p. ej. modificar forma de devolución).
    """

    codigo: str
    service_id: int
    servicesubcategory_id: int
    template_id: int
    service_family_id: int = 30
    con_adjunto: bool = True


SPECS: dict[str, TicketSpec] = {
    "4ta": TicketSpec("4ta", service_id=218, servicesubcategory_id=1195, template_id=34),
    "5ta": TicketSpec("5ta", service_id=218, servicesubcategory_id=1196, template_id=35),
    "601": TicketSpec("601", service_id=217, servicesubcategory_id=2081, template_id=13),
    "601_completo": TicketSpec("601_completo", service_id=217,
                               servicesubcategory_id=1193, template_id=14),
    "modificar": TicketSpec("modificar", service_id=95, servicesubcategory_id=2445,
                            template_id=144, con_adjunto=False),
}


@dataclass
class DatosModificar:
    """Datos del ticket de modificación de modalidad de devolución (sin adjunto)."""

    modalidad: str        # debe ser una de MODALIDADES (valor exacto, con su espacio)
    ruc: str
    nro_orden: str
    cci: str | None = None
    tipo: str = "modificar"


# Opciones del dropdown A01 tal como las espera Mesa de Ayuda (la 2ª lleva un espacio
# inicial; debe enviarse exactamente así).
MODALIDADES: tuple[str, ...] = (
    "De Abono en Cuenta a Cheque",
    " De Cheque a Abono en Cuenta",
    "De Cheque a OPF",
    "De OPF a Cheque",
)

# Modalidad que exige CCI (según la nota de la plantilla).
_MODALIDAD_REQUIERE_CCI = "De Cheque a Abono en Cuenta"


def requiere_cci(modalidad: str) -> bool:
    """True si la modalidad exige ingresar el CCI (cheque -> abono en cuenta)."""
    return modalidad.strip() == _MODALIDAD_REQUIERE_CCI

# Wrapper común de la descripción (HTML con entidades, como en el portal).
_DESC_WRAPPER = (
    "<p>Buenos d&iacute;as,<br />\n{cuerpo}<br />\nMuchas gracias.</p>\n"
)


def spec_de(tipo: str) -> TicketSpec:
    """Devuelve el ``TicketSpec`` del tipo. Lanza ``ValueError`` si no existe."""
    try:
        return SPECS[tipo]
    except KeyError:
        raise ValueError(f"Tipo de ticket desconocido: {tipo!r}") from None


def resolver_periodos(datos: DatosTicket, hoy: date | None = None) -> tuple[int, int]:
    """(inicio, fin) en ``YYYYMM`` según el tipo de ticket."""
    if datos.tipo == "4ta":
        return periodos.periodos_4ta(datos.ejercicio, hoy)
    return periodos.periodos_anuales(datos.ejercicio)


def contenido_txt(datos: DatosTicket, hoy: date | None = None) -> str:
    """Contenido del archivo ``.txt`` a adjuntar, según el tipo."""
    ini, fin = resolver_periodos(datos, hoy)
    if datos.tipo == "4ta":
        return f"{datos.ruc}|{ini}|{fin}|"
    if datos.tipo == "601_completo":
        return f"{datos.ruc_empleador}|{ini}|{fin}|"
    doc = periodos.documento_trabajador(datos.ruc, datos.doc_override)
    if datos.tipo == "5ta":
        return f"{doc}|{ini}|{fin}|"
    if datos.tipo == "601":
        return f"{datos.ruc_empleador}|{doc}|{ini}|{fin}|"
    raise ValueError(f"Tipo de ticket desconocido: {datos.tipo!r}")


def titulo(datos: DatosTicket) -> str:
    """Título del ticket según el tipo."""
    if datos.tipo == "4ta":
        return f"DESCARGA RENTAS DE 4TA_OF {datos.of}"
    if datos.tipo == "5ta":
        return f"DESCARGA RENTAS DE 5TA_OF {datos.of}"
    if datos.tipo in ("601", "601_completo"):
        return f"Solicito descarga de PDT 601_OF {datos.of}"
    raise ValueError(f"Tipo de ticket desconocido: {datos.tipo!r}")


def descripcion(datos: DatosTicket, hoy: date | None = None) -> str:
    """Descripción HTML del ticket (replica el formato del portal)."""
    if datos.tipo == "4ta":
        ini, fin = resolver_periodos(datos, hoy)
        cuerpo = (
            f"Solicito la descarga de rentas de cuarta categor&iacute;a del "
            f"contribuyente {datos.nombre} con RUC {datos.ruc}, correspondiente al "
            f"ejercicio {ini // 100}-{fin // 100}, a fin de atender la solicitud de "
            f"devoluci&oacute;n."
        )
    elif datos.tipo == "5ta":
        cuerpo = (
            f"Solicito la descarga de rentas de quinta categor&iacute;a del "
            f"contribuyente {datos.nombre} con RUC {datos.ruc}, correspondiente al "
            f"ejercicio {datos.ejercicio}, a fin de atender la solicitud de "
            f"devoluci&oacute;n."
        )
    elif datos.tipo in ("601", "601_completo"):
        cuerpo = (
            f"Solicito la descarga del PDT 601 del empleador {datos.nombre_empleador} "
            f"con RUC {datos.ruc_empleador}, por los periodos de enero a diciembre de "
            f"{datos.ejercicio}, con relaci&oacute;n al contribuyente {datos.nombre} "
            f"con RUC {datos.ruc}, a fin de atender la solicitud de devoluci&oacute;n."
        )
    else:
        raise ValueError(f"Tipo de ticket desconocido: {datos.tipo!r}")
    return _DESC_WRAPPER.format(cuerpo=cuerpo)


def nombre_archivo_txt(datos: DatosTicket) -> str:
    """Nombre por defecto del ``.txt`` adjunto."""
    return f"{datos.tipo}_{datos.ruc}_{datos.ejercicio}.txt"


# --- Tipo MODIFICAR (modalidad de devolución) ---

# Wrapper de la descripción para el ticket de modificación (replica el portal).
_DESC_MODIFICAR = (
    "<p>Buenos d&iacute;as,<br />\n"
    "Por la presente se solicita modificar la forma de devoluci&oacute;n {mod} "
    "conforme lo se&ntilde;alado previamente.<br />\n"
    "Muchas gracias.</p>\n\n<p>Saludos.<br />\n&nbsp;</p>\n"
)


def titulo_modificar(datos: DatosModificar) -> str:
    """Título (estático) del ticket de modificación de modalidad."""
    return "MODIFICAR MODALIDAD DE DEVOLUCIÓN"


def descripcion_modificar(datos: DatosModificar) -> str:
    """Descripción HTML; interpola la modalidad elegida en mayúsculas."""
    return _DESC_MODIFICAR.format(mod=datos.modalidad.strip().upper())


def user_data_modificar(datos: DatosModificar) -> dict[str, str]:
    """Campos de plantilla (A01..A04) del ticket de modificación."""
    return {
        "A01": datos.modalidad,
        "A02": datos.ruc,
        "A03": datos.nro_orden,
        "A04": datos.cci or "",
    }
