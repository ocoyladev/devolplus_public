"""Tests del adaptador de demostración y de la resolución del adaptador activo."""
from __future__ import annotations

import pytest

from MACRO.adapters import BackofficeAdapter, get_adapter
from MACRO.adapters.demo import DemoAdapter


def test_get_adapter_devuelve_demo_por_defecto(monkeypatch):
    monkeypatch.delenv("BACKOFFICE_ADAPTER", raising=False)
    assert isinstance(get_adapter(), DemoAdapter)


def test_get_adapter_rechaza_un_nombre_desconocido(monkeypatch):
    monkeypatch.setenv("BACKOFFICE_ADAPTER", "produccion")
    with pytest.raises(RuntimeError, match="Adaptador desconocido"):
        get_adapter()


def test_demo_adapter_cumple_el_protocolo():
    assert isinstance(DemoAdapter(), BackofficeAdapter)


def test_verificar_servicios_devuelve_ambas_sesiones():
    sesion, cookie = DemoAdapter().verificar_servicios()
    assert sesion is not None
    assert cookie is not None


def test_verificar_servicios_respeta_los_flags():
    sesion, cookie = DemoAdapter().verificar_servicios(check_workflow=False)
    assert sesion is not None
    assert cookie is None


def test_descargar_escribe_el_artefacto(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "MACRO.funciones.funciones_casos.get_case_folder",
        lambda row: str(tmp_path / row["num_doc"]),
    )
    r = DemoAdapter().descargar("3154500", "ri")

    assert r["ok"] is True
    contenido = (tmp_path / "3154500" / "ri_3154500.txt").read_text(encoding="utf8")
    assert "no corresponde a ningún expediente real" in contenido


def test_descargar_reporta_progreso(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "MACRO.funciones.funciones_casos.get_case_folder",
        lambda row: str(tmp_path / row["num_doc"]),
    )
    eventos = []
    DemoAdapter().descargar("3154500", "ri", progreso=lambda *a: eventos.append(a))
    assert len(eventos) == 5
    assert eventos[-1][0] == eventos[-1][1]  # termina en done == total


def test_cargar_casos_separa_los_no_encontrados():
    r = DemoAdapter().cargar_casos(["3154500", "0000000"])
    assert r["cargados"] == 1
    assert r["no_encontrados"] == ["0000000"]
