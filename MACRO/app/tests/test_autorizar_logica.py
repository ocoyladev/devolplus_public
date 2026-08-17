"""Tests de la lógica de autorización (parseo, conflictos y anexo).

Los datos son sintéticos: los RUC llevan dígito verificador inválido a propósito
(ver :mod:`demo.seed`), de modo que no corresponden a ningún contribuyente real.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from MACRO.flujos.flujo_autorizar import (
    _a_float,
    _decisiones_a_aplicar,
    _decisiones_c64_a_aplicar,
    _filas_anexo,
    _parsear_entrada_fecha,
    evaluar_conflicto_autorizar,
    evaluar_conflicto_c64,
    generar_anexo_devoluciones,
    parsear_entradas_autorizar,
    prechequear_autorizar,
)

RUC_DEMO = "10412345670"


# --- parseo de entradas -----------------------------------------------------

def test_parsear_linea_completa():
    decisiones, errores = parsear_entradas_autorizar(
        ["3154500;Aut.total;1250.50;15/06/2026"]
    )
    assert errores == []
    assert decisiones == [{
        "num_doc": "3154500",
        "resultado": "Aut.total",
        "monto": 1250.50,
        "fecha": date(2026, 6, 15),
    }]


def test_parsear_acepta_tabulacion_como_separador():
    decisiones, _ = parsear_entradas_autorizar(["3154501\tDenegado\t0\t01/01/2026"])
    assert decisiones[0]["num_doc"] == "3154501"
    assert decisiones[0]["resultado"] == "Denegado"


def test_parsear_ignora_lineas_vacias():
    decisiones, errores = parsear_entradas_autorizar(["", "   ", "3154502;Aut.total"])
    assert len(decisiones) == 1
    assert errores == []


def test_parsear_reporta_linea_sin_num_doc():
    _decisiones, errores = parsear_entradas_autorizar([";Aut.total;100"])
    assert errores == [{"linea": 1, "mensaje": "Falta el número de documento"}]


def test_parsear_usa_hoy_cuando_falta_la_fecha():
    hoy = date(2026, 8, 17)
    decisiones, _ = parsear_entradas_autorizar(["3154503;Aut.total;10"], hoy=hoy)
    assert decisiones[0]["fecha"] == hoy


@pytest.mark.parametrize("texto", ["15/06/2026", "15-06-2026", "2026-06-15"])
def test_parsear_fecha_acepta_los_formatos_soportados(texto):
    assert _parsear_entrada_fecha(texto) == date(2026, 6, 15)


def test_parsear_fecha_invalida_devuelve_none():
    assert _parsear_entrada_fecha("32/13/2026") is None


@pytest.mark.parametrize(
    ("entrada", "esperado"), [("1250.50", 1250.50), ("1,250.50", 1250.50),
                              ("", 0.0), ("n/a", 0.0), (None, 0.0)],
)
def test_a_float_normaliza_montos(entrada, esperado):
    assert _a_float(entrada) == esperado


# --- conflictos -------------------------------------------------------------

def test_conflicto_si_autoriza_sin_saldo_en_c89_ni_c65():
    assert evaluar_conflicto_autorizar("Aut.total", c89=0, c65=0) is True


def test_sin_conflicto_si_alguna_casilla_es_positiva():
    assert evaluar_conflicto_autorizar("Aut.total", c89=100, c65=0) is False
    assert evaluar_conflicto_autorizar("Aut.total", c89=0, c65=100) is False


def test_sin_conflicto_si_el_resultado_no_autoriza():
    assert evaluar_conflicto_autorizar("Denegado", c89=0, c65=0) is False


def test_conflicto_c64_solo_cuando_autoriza_sin_saldo():
    assert evaluar_conflicto_c64("Aut.parcial", c64=0) is True
    assert evaluar_conflicto_c64("Aut.parcial", c64=50) is False
    assert evaluar_conflicto_c64("Improcedente", c64=0) is False


def test_valores_no_numericos_se_tratan_como_cero():
    assert evaluar_conflicto_autorizar("Aut.total", c89="n/a", c65="") is True


# --- prechequeo -------------------------------------------------------------

def test_prechequear_resume_decisiones_y_errores():
    r = prechequear_autorizar(["3154500;Aut.total;100;15/06/2026", ";sin doc"])
    assert r["ok"] is False
    assert len(r["decisiones"]) == 1
    assert len(r["errores"]) == 1


def test_prechequear_separa_los_conflictos_por_casilla():
    """El router mapea ``c65`` a ``ConflictoAutorizar`` y ``c64`` a
    ``ConflictoC64``: cada lista debe traer exactamente los campos de su
    esquema, o el endpoint falla al serializar."""
    r = prechequear_autorizar(["3154500;Aut.total;0"])

    assert set(r) >= {"c65", "c64", "decisiones", "errores", "ok"}
    assert [c["num_doc"] for c in r["c65"]] == ["3154500"]
    assert set(r["c65"][0]) == {"num_doc", "per_doc", "nombre", "c89"}
    assert set(r["c64"][0]) == {"num_doc", "per_doc", "nombre", "g58"}


def test_prechequear_sin_conflicto_cuando_el_resultado_no_autoriza():
    r = prechequear_autorizar(["3154500;Denegado;0"])
    assert r["c65"] == []
    assert r["c64"] == []


# --- filtrado de decisiones -------------------------------------------------

def test_decisiones_a_aplicar_respeta_la_marca_del_usuario():
    decisiones = [
        {"num_doc": "A", "aplicar": True},
        {"num_doc": "B", "aplicar": False},
        {"num_doc": "C"},  # sin marca: se aplica por defecto
    ]
    assert [d["num_doc"] for d in _decisiones_a_aplicar(decisiones)] == ["A", "C"]


def test_decisiones_c64_a_aplicar_usa_el_mismo_criterio():
    assert _decisiones_c64_a_aplicar([{"num_doc": "A", "aplicar": False}]) == []
    assert _decisiones_c64_a_aplicar(None) == []


# --- anexo ------------------------------------------------------------------

def test_filas_anexo_extrae_las_columnas_esperadas():
    df = pd.DataFrame([{
        "num_doc": "3154500", "num_ruc": RUC_DEMO, "ddp_nombre": "QUISPE FLORES, ANA",
        "mto_solicitado": 1250.5, "resultado": "Aut.total", "sobrante": "ignorada",
    }])
    filas = _filas_anexo(df)
    assert filas == [{
        "num_doc": "3154500", "num_ruc": RUC_DEMO, "ddp_nombre": "QUISPE FLORES, ANA",
        "mto_solicitado": "1250.5", "resultado": "Aut.total",
    }]


def test_filas_anexo_con_dataframe_vacio_devuelve_lista_vacia():
    assert _filas_anexo(pd.DataFrame()) == []
    assert _filas_anexo(None) == []


def test_filas_anexo_no_emite_nan_como_texto():
    df = pd.DataFrame([{"num_doc": "3154500", "num_ruc": RUC_DEMO,
                        "ddp_nombre": None, "mto_solicitado": 10, "resultado": ""}])
    assert _filas_anexo(df)[0]["ddp_nombre"] == ""


def test_generar_anexo_escribe_csv_con_cabecera(tmp_path):
    filas = [{"num_doc": "3154500", "num_ruc": RUC_DEMO,
              "ddp_nombre": "QUISPE FLORES, ANA", "mto_solicitado": "1250.5",
              "resultado": "Aut.total"}]

    ruta = generar_anexo_devoluciones(filas, str(tmp_path))

    contenido = (tmp_path / "anexo_devoluciones.csv").read_text(encoding="utf8")
    assert ruta.endswith("anexo_devoluciones.csv")
    assert contenido.splitlines()[0].startswith("num_doc,num_ruc")
    assert RUC_DEMO in contenido


def test_generar_anexo_sin_filas_no_crea_archivo(tmp_path):
    assert generar_anexo_devoluciones([], str(tmp_path)) is None
    assert list(tmp_path.iterdir()) == []
