"""Tests del generador de datos sintéticos.

La propiedad crítica es que ningún RUC generado pueda corresponder a un
contribuyente real: todos deben fallar la validación módulo 11.
"""
from __future__ import annotations

import pytest

from demo.seed import (
    FORMAS_DEVOLUCION,
    FORMULARIOS,
    digito_verificador,
    es_ruc_valido,
    generar_casos,
)


def test_ningun_ruc_generado_es_valido():
    """Invariante de seguridad: los RUC sintéticos no deben validar."""
    casos = generar_casos(200)
    invalidos = [c["num_ruc"] for c in casos if es_ruc_valido(c["num_ruc"])]
    assert invalidos == [], f"RUC potencialmente reales: {invalidos}"


def test_los_ruc_conservan_la_forma_real():
    for c in generar_casos(50):
        ruc = c["num_ruc"]
        assert len(ruc) == 11
        assert ruc.isdigit()
        assert ruc[:2] in ("10", "20")


def test_generacion_determinista():
    assert generar_casos(20) == generar_casos(20)


def test_semillas_distintas_dan_conjuntos_distintos():
    a = [c["num_ruc"] for c in generar_casos(20, semilla=1)]
    b = [c["num_ruc"] for c in generar_casos(20, semilla=2)]
    assert a != b


def test_num_doc_es_unico():
    casos = generar_casos(60)
    assert len({c["num_doc"] for c in casos}) == len(casos)


def test_dominios_de_valores_respetados():
    for c in generar_casos(60):
        assert c["cod_for"] in FORMULARIOS
        assert c["forma_dev"] in FORMAS_DEVOLUCION
        assert c["per_doc"].endswith("13")
        assert c["mto_solicitado"] > 0


@pytest.mark.parametrize(
    ("base", "esperado"),
    [("2010000006", digito_verificador("2010000006"))],
)
def test_digito_verificador_es_coherente(base, esperado):
    assert es_ruc_valido(f"{base}{esperado}")
    assert not es_ruc_valido(f"{base}{(esperado + 1) % 10}")


def test_digito_verificador_rechaza_longitud_incorrecta():
    with pytest.raises(ValueError):
        digito_verificador("123")
