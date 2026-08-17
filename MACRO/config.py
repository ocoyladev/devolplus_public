import re

# Constantes generales
PENDIENTES_FILENAME = "descargas_pendiente.txt"
NBSP = chr(160)
SKIP_PERSONALIZADO_PREFIXES = ("pag_1ra_", "rbr_2da_", "ret_2da_", "sal_fav_")

# Formatos de moneda
CURRENCY_EXCEL_FORMAT = '"S/" #,##0.00'

# Constantes para RxH
RXH_ESTADOS = {"0": "NO ANULADO", "1": "REVERTIDO"}
RXH_MONEDAS = {"PEN": "S/", "USD": "$"}
RXH_CURRENCY_FORMATS = {
    "S/": '"S/" #,##0.00',
    "$": '"$" #,##0.00',
}

# Columnas de moneda para archivos personalizados
CURRENCY_COLS = {
    "REMUNERACION MENSUAL","PAGOS SIN INTERESES","PAGO TOTAL",
    "INGRESO ATRIBUIDO","RETENCION",
    "DEVOLUCION POR EXCESO DE RETENCION",
    "RETENCION POR RECIBOS, DIETAS, OTROS COMPROBANTES Y NOTAS DE CREDITO",
    "MONTO DE LA RETENCION"
}

# Rutas por defecto
DEFAULT_PATH_DESCARGAS = r"D:\DEVOLUCIONES"
DEFAULT_PATH_RI = r"D:\RI"
DEFAULT_PATH_AUTORIZAR = r"D:\ENVIAR_AUTORIZAR"
DEFAULT_PATH_ARCHIVO = r"D:\ARCHIVO"

# Ejecutable de SIRAT (automatización RSIRAT: REF/Tiempos y Antecedentes).
DEFAULT_PATH_SIRAT_EXE = r"C:\RSIRAT_new\sirat.exe"

