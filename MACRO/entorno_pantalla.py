"""Perfiles de pantalla y coordenadas de la firma automática.

Fuente única de las combinaciones escala/resolución admitidas y de las
coordenadas de clic. Consumido por el router web (MACRO/app/routers/entorno.py)
y por la firma del expediente. La lectura de la
pantalla usa APIs de Windows (import diferido); en otros sistemas devuelve un
error y ``detectar_pantalla`` retorna ``None``.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

Coord = tuple[int, int]
CoordsFirma = tuple[Coord, Coord, Coord]


@dataclass(frozen=True)
class PerfilPantalla:
    escala: int
    ancho: int
    alto: int
    coords: CoordsFirma  # (A: 1er botón, B: 2º botón, C: "Aceptar" subventana)

    @property
    def clave(self) -> str:
        return f"{self.escala}@{self.ancho}x{self.alto}"


PERFILES: tuple[PerfilPantalla, ...] = (
    PerfilPantalla(125, 1920, 1200, ((1035, 535), (1082, 685), (930, 707))),
    PerfilPantalla(100, 1920, 1080, ((929, 478), (1068, 633), (943, 631))),
)


def perfil_para(escala: int, ancho: int, alto: int) -> PerfilPantalla | None:
    """Perfil admitido que coincide exactamente con escala + resolución, o None."""
    for p in PERFILES:
        if p.escala == escala and p.ancho == ancho and p.alto == alto:
            return p
    return None


def perfiles_admitidos_texto() -> str:
    """Texto legible con los perfiles admitidos (para el motivo de la UI)."""
    return " o ".join(f"{p.escala}%/{p.ancho}×{p.alto}" for p in PERFILES)


@dataclass(frozen=True)
class LecturaPantalla:
    escala: int | None = None
    ancho: int | None = None
    alto: int | None = None
    error: str | None = None


def leer_pantalla() -> LecturaPantalla:
    """Lee escala DPI y resolución física de la pantalla principal (Windows)."""
    if sys.platform != "win32":
        return LecturaPantalla(
            error="La firma automática solo está disponible en Windows."
        )
    try:
        import ctypes

        user32 = ctypes.windll.user32
        try:
            dpi = int(user32.GetDpiForSystem())
        except AttributeError:
            hdc = user32.GetDC(0)
            LOGPIXELSX = 88
            dpi = int(ctypes.windll.gdi32.GetDeviceCaps(hdc, LOGPIXELSX))
            user32.ReleaseDC(0, hdc)
        escala = round(dpi / 96 * 100)

        class _DEVMODE(ctypes.Structure):
            _fields_ = [
                ("dmDeviceName", ctypes.c_wchar * 32),
                ("dmSpecVersion", ctypes.c_ushort),
                ("dmDriverVersion", ctypes.c_ushort),
                ("dmSize", ctypes.c_ushort),
                ("dmDriverExtra", ctypes.c_ushort),
                ("dmFields", ctypes.c_ulong),
                ("dmOrientation", ctypes.c_short),
                ("dmPaperSize", ctypes.c_short),
                ("dmPaperLength", ctypes.c_short),
                ("dmPaperWidth", ctypes.c_short),
                ("dmScale", ctypes.c_short),
                ("dmCopies", ctypes.c_short),
                ("dmDefaultSource", ctypes.c_short),
                ("dmPrintQuality", ctypes.c_short),
                ("dmColor", ctypes.c_short),
                ("dmDuplex", ctypes.c_short),
                ("dmYResolution", ctypes.c_short),
                ("dmTTOption", ctypes.c_short),
                ("dmCollate", ctypes.c_short),
                ("dmFormName", ctypes.c_wchar * 32),
                ("dmLogPixels", ctypes.c_ushort),
                ("dmBitsPerPel", ctypes.c_ulong),
                ("dmPelsWidth", ctypes.c_ulong),
                ("dmPelsHeight", ctypes.c_ulong),
                ("dmDisplayFlags", ctypes.c_ulong),
                ("dmDisplayFrequency", ctypes.c_ulong),
                ("dmICMMethod", ctypes.c_ulong),
                ("dmICMIntent", ctypes.c_ulong),
                ("dmMediaType", ctypes.c_ulong),
                ("dmDitherType", ctypes.c_ulong),
                ("dmReserved1", ctypes.c_ulong),
                ("dmReserved2", ctypes.c_ulong),
                ("dmPanningWidth", ctypes.c_ulong),
                ("dmPanningHeight", ctypes.c_ulong),
            ]

        devmode = _DEVMODE()
        devmode.dmSize = ctypes.sizeof(_DEVMODE)
        ENUM_CURRENT_SETTINGS = -1
        if not user32.EnumDisplaySettingsW(
            None, ENUM_CURRENT_SETTINGS, ctypes.byref(devmode)
        ):
            return LecturaPantalla(
                escala=escala,
                error="No se pudo leer la resolución física de la pantalla.",
            )
        return LecturaPantalla(
            escala=escala, ancho=int(devmode.dmPelsWidth), alto=int(devmode.dmPelsHeight)
        )
    except Exception as e:  # noqa: BLE001 — ante cualquier fallo, se deshabilita
        return LecturaPantalla(error=f"No se pudo detectar la pantalla: {e}")


def detectar_pantalla() -> PerfilPantalla | None:
    """Perfil admitido según la pantalla actual, o None si no coincide/no se lee."""
    lec = leer_pantalla()
    if lec.escala is None or lec.ancho is None or lec.alto is None:
        return None
    return perfil_para(lec.escala, lec.ancho, lec.alto)
