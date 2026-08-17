"""Generador de datos sintéticos para el modo demo.

Genera casos que respetan la *estructura* de los datos reales (tipos, longitudes,
dominios de valores) sin corresponder a ninguna persona ni expediente real.

Garantía de no colisión
-----------------------
Los RUC generados llevan **dígito verificador inválido a propósito**. El RUC
peruano valida con módulo 11 sobre los 10 primeros dígitos; aquí se calcula el
dígito correcto y se sustituye por otro distinto. El resultado tiene la forma
correcta (11 dígitos, prefijo 10/20) pero no puede corresponder a ningún
contribuyente inscrito. :func:`digito_verificador` y :func:`es_ruc_valido`
permiten verificar esta propiedad desde los tests.

El generador es determinista: la misma ``semilla`` produce siempre el mismo
conjunto, para que los tests y las capturas de pantalla sean reproducibles.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

# Pesos del algoritmo módulo 11 para el RUC peruano (10 primeros dígitos).
_PESOS_RUC = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)

_APELLIDOS = [
    "QUISPE", "MAMANI", "HUAMAN", "FLORES", "CONDORI", "VARGAS", "ROJAS",
    "CHAVEZ", "PAREDES", "ESPINOZA", "SALAZAR", "CACERES", "ZEVALLOS", "ÑAHUI",
]
_NOMBRES = [
    "ANA", "LUIS", "CARMEN", "JORGE", "ROSA", "MIGUEL", "ELENA", "PEDRO",
    "SOFIA", "RAUL", "TERESA", "IVAN",
]
_EMPRESAS = [
    "COMERCIAL", "SERVICIOS", "INVERSIONES", "DISTRIBUIDORA", "CONSTRUCTORA",
]
_SUFIJOS = ["SAC", "EIRL", "SRL", "SA"]

# Dominios de valores tomados de la estructura real (códigos, no datos).
FORMULARIOS = ["1649", "4949"]
TIPOS_SOLICITUD = ["02", "09", "40"]
FORMAS_DEVOLUCION = ["Abono cta", "Cheque", "OPF"]
RESULTADOS = [
    "Aut.total", "Aut.parcial", "Denegado", "Improcedente", "",
]
ESTADOS_CARTA = ["", "Notificada", "Pendiente", "Vencida"]


def digito_verificador(base10: str) -> int:
    """Dígito verificador módulo 11 de los 10 primeros dígitos de un RUC."""
    if len(base10) != 10 or not base10.isdigit():
        raise ValueError("Se esperan exactamente 10 dígitos")
    suma = sum(int(d) * p for d, p in zip(base10, _PESOS_RUC))
    resto = 11 - (suma % 11)
    return {10: 0, 11: 1}.get(resto, resto)


def es_ruc_valido(ruc: str) -> bool:
    """``True`` si el RUC tiene 11 dígitos y dígito verificador correcto."""
    if len(ruc) != 11 or not ruc.isdigit():
        return False
    return digito_verificador(ruc[:10]) == int(ruc[10])


def _ruc_invalido(rng: random.Random, prefijo: str) -> str:
    """RUC con forma válida y dígito verificador deliberadamente incorrecto."""
    base = prefijo + "".join(str(rng.randint(0, 9)) for _ in range(8))
    correcto = digito_verificador(base)
    # Cualquier dígito distinto del correcto invalida el RUC.
    incorrecto = (correcto + rng.randint(1, 9)) % 10
    if incorrecto == correcto:  # pragma: no cover - defensivo
        incorrecto = (correcto + 1) % 10
    return f"{base}{incorrecto}"


def _nombre_pn(rng: random.Random) -> str:
    return (
        f"{rng.choice(_APELLIDOS)} {rng.choice(_APELLIDOS)}, "
        f"{rng.choice(_NOMBRES)} {rng.choice(_NOMBRES)}"
    )


def _nombre_pj(rng: random.Random) -> str:
    return (
        f"{rng.choice(_EMPRESAS)} {rng.choice(_APELLIDOS).capitalize()} "
        f"{rng.choice(_SUFIJOS)}"
    )


def generar_casos(cantidad: int = 60, semilla: int = 20260817) -> list[dict[str, Any]]:
    """Genera ``cantidad`` casos sintéticos deterministas.

    Las claves coinciden con las columnas de ``tabla_bd`` / ``tabla_asign`` para
    que el resto de la aplicación no distinga el origen de los datos.
    """
    rng = random.Random(semilla)
    hoy = date(2026, 8, 17)
    casos: list[dict[str, Any]] = []

    for i in range(cantidad):
        persona_juridica = rng.random() < 0.25
        prefijo = "20" if persona_juridica else "10"
        ruc = _ruc_invalido(rng, prefijo)
        nombre = _nombre_pj(rng) if persona_juridica else _nombre_pn(rng)

        fec_doc = hoy - timedelta(days=rng.randint(30, 400))
        ejercicio = fec_doc.year - 1
        resultado = rng.choice(RESULTADOS)
        tiene_ri = resultado.startswith("Aut") or resultado in ("Denegado", "Improcedente")

        casos.append(
            {
                "of_devolucion": f"OF-{i + 1:03d}",
                "num_doc": f"{3154500 + i}",
                "num_ruc": ruc,
                "ddp_nombre": nombre,
                "fec_doc": fec_doc.strftime("%d/%m/%Y"),
                "cod_tri": "3031",
                "desc_tributo": "RENTA PERSONA NATURAL",
                "per_doc": f"{ejercicio}13",
                "cod_tip_sol": rng.choice(TIPOS_SOLICITUD),
                "mto_solicitado": round(rng.uniform(80, 9500), 2),
                "cod_dep": "0023",
                "num_dev": f"{rng.randint(1000000, 9999999)}",
                "cod_for": rng.choice(FORMULARIOS),
                "cod_for_aso": "",
                "forma_dev": rng.choice(FORMAS_DEVOLUCION),
                "vcto_ind": (fec_doc + timedelta(days=45)).strftime("%d/%m/%Y"),
                "carta": f"C-{i + 1:03d}" if rng.random() < 0.6 else "",
                "estado_carta": rng.choice(ESTADOS_CARTA),
                "ri": f"RI-{i + 1:04d}-{ejercicio}" if tiene_ri else "",
                "resultado": resultado,
                "nom_supervisor": "SUPERVISOR DEMO",
                "cod_area_eva": "0001",
                "observacion": "",
            }
        )

    return casos


def sembrar(db_path: str | None = None, cantidad: int = 60) -> int:
    """Siembra la BD local con casos sintéticos. Devuelve cuántos insertó.

    Es idempotente: si la tabla ya tiene filas, no hace nada. Para regenerar,
    borre el archivo de base de datos y vuelva a llamar.
    """
    import sqlite3

    from MACRO.database import DB_FILE, init_db

    init_db()
    conn = sqlite3.connect(db_path or DB_FILE)
    try:
        ya = conn.execute("SELECT COUNT(*) FROM tabla_bd").fetchone()[0]
        if ya:
            return 0
        casos = generar_casos(cantidad)
        cols = [
            "of_devolucion", "num_doc", "num_ruc", "ddp_nombre", "fec_doc",
            "cod_tri", "desc_tributo", "per_doc", "cod_tip_sol",
            "mto_solicitado", "cod_dep", "num_dev", "cod_for", "cod_for_aso",
        ]
        conn.executemany(
            f"INSERT INTO tabla_bd ({','.join(cols)}) "
            f"VALUES ({','.join('?' * len(cols))})",
            [tuple(c[k] for k in cols) for c in casos],
        )
        conn.commit()
        return len(casos)
    finally:
        conn.close()


if __name__ == "__main__":  # pragma: no cover
    print(f"{sembrar()} casos sintéticos insertados")
