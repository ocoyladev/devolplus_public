"""Esquemas de procesos masivos (operan sobre una lista de num_doc)."""
from __future__ import annotations

from pydantic import BaseModel


class ProcesoDocsRequest(BaseModel):
    num_docs: list[str]


class CargaExpedientesRequest(BaseModel):
    num_docs: list[str]
    ejecutar_firma_auto: bool = False


class DecisionAutorizar(BaseModel):
    accion: str  # "confirmar" | "aplicar_c89" | "aplicar_valor"
    valor: float | None = None


class DecisionC64(BaseModel):
    accion: str  # "aplicar_g58" | "aplicar_valor"
    valor: float | None = None


class AutorizarRequest(BaseModel):
    # Cada línea: 'num_doc', 'num_doc|fecha_final' o 'num_doc|fecha_inicial|fecha_final'.
    lineas: list[str]
    # num_doc -> decisión de confirmación (solo para casos en conflicto C89/C65).
    decisiones: dict[str, DecisionAutorizar] = {}
    # num_doc -> decisión de corrección de C64 (casos autorizados con C64==0).
    decisiones_c64: dict[str, DecisionC64] = {}


class PreCheckRequest(BaseModel):
    lineas: list[str]


class ConflictoAutorizar(BaseModel):
    num_doc: str
    per_doc: str
    nombre: str
    c89: float


class ConflictoC64(BaseModel):
    num_doc: str
    per_doc: str
    nombre: str
    g58: float


class PreCheckResponse(BaseModel):
    conflictos: list[ConflictoAutorizar]
    conflictos_c64: list[ConflictoC64] = []


class VerificarEchasquiRequest(BaseModel):
    num_docs: list[str]


class EchasquiEstado(BaseModel):
    denom: str
    clasificacion: str
    estado: str
    subible: bool = False


class CasoEchasqui(BaseModel):
    num_doc: str
    num_dev: str
    num_ruc: str
    nombre: str
    tipo_exp: str = ""
    echasquis: list[EchasquiEstado] = []
    sin_echasqui: bool = False
    error: str = ""


class VerificarEchasquiResponse(BaseModel):
    casos: list[CasoEchasqui]


class ItemEchasquiPendiente(BaseModel):
    num_doc: str
    num_dev: str
    num_ruc: str
    denom: str


class SubirEchasquiRequest(BaseModel):
    items: list[ItemEchasquiPendiente]


class AlertaValidacion(BaseModel):
    codigo: str
    severidad: str
    mensaje: str
    accion: str = ""
    # Insumo de la acción cuando no basta el num_doc (p. ej. la denominación del
    # echasqui a subir por vía especial).
    item: str = ""


class InsumoFinal(BaseModel):
    completo: bool
    faltantes: list[str] = []
    puede_foliar: bool = False


class ExpEchasquiEstado(BaseModel):
    registrado: bool
    valor: str = ""
    autoregistrado: bool = False


class EchasquiItem(BaseModel):
    denom: str
    clasificacion: str = ""
    estado: str = ""
    subible: bool = False


class CargaLocal(BaseModel):
    reportes: bool = False
    cedula: bool = False


class Carga1649(BaseModel):
    aplica: bool
    local: CargaLocal = CargaLocal()
    remoto: str = "na"
    remoto_reportes: bool = False
    remoto_cedula: bool = False
    # "si" | "no" | "desconocido" — ambos PDF deben quedar en "no" (Uso Interno).
    visible_reportes: str = "desconocido"
    visible_cedula: str = "desconocido"


class PatronIndispensable(BaseModel):
    patron: str
    encontrado: bool


class Indispensables(BaseModel):
    raiz: list[PatronIndispensable] = []
    subcarpetas: dict[str, list[PatronIndispensable]] = {}


class CasoValidacion(BaseModel):
    num_doc: str
    num_dev: str = ""
    num_ruc: str = ""
    nombre: str = ""
    of_devolucion: str = ""
    tipo_exp: str = ""
    cod_tip_sol: str = ""
    # Rectificatoria (tipo 12): hereda el armado de su solicitud de origen, cuyo
    # num_doc queda en origen_tipo12 ("" si no se pudo resolver).
    es_tipo12: bool = False
    origen_tipo12: str = ""
    is_of_multiple: bool = False
    carpeta_existe: bool = False
    paso_pptt: bool = False
    insumo_final: InsumoFinal
    exp_echasqui: ExpEchasquiEstado
    echasquis: list[EchasquiItem] = []
    carga_1649: Carga1649
    indispensables: Indispensables
    alertas: list[AlertaValidacion] = []
    nivel: str = "ok"
    error: str = ""


class ValidarArchivoRequest(BaseModel):
    num_docs: list[str]


class ValidarArchivoResponse(BaseModel):
    casos: list[CasoValidacion] = []


class AccionSubsanar(BaseModel):
    num_doc: str
    accion: str


class SubsanarRequest(BaseModel):
    acciones: list[AccionSubsanar]


class ExportarRequest(BaseModel):
    casos: list[CasoValidacion]


class AbrirCarpetaRequest(BaseModel):
    num_doc: str
