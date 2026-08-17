"""Barrido de contratos: ejercita todos los endpoints sin mocks.

El resto de la suite mockea los flujos, así que verifica cada router de forma
aislada. Eso deja pasar los desajustes de contrato: un flujo que devuelve
``{"items": …}`` cuando el router lee ``res["casos"]``, o un dict al que le falta
un campo obligatorio del modelo de respuesta. Nada de eso rompe un test con
mocks, pero sí rompe la aplicación en cuanto se usa.

Este test recorre las rutas registradas, arma un cuerpo válido desde el propio
esquema de request y comprueba que ninguna responda 5xx ni lance. No valida la
semántica de la respuesta — para eso están los tests por router; valida que la
cadena router → flujo → adaptador → esquema de respuesta encaje.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic_core import PydanticUndefined

from MACRO.app.server import create_app

# Fila de caso con los campos que los flujos suelen leer.
FILA = {
    "of_devolucion": "OF-001", "num_doc": "3154500", "num_ruc": "10412345670",
    "ddp_nombre": "DEMO PRUEBA", "per_doc": "202513", "cod_for": "1649",
    "num_dev": "1234567", "cod_tip_sol": "02",
}

# Campos cuyo valor genérico no serviría porque el flujo los valida contra un
# dominio cerrado (y un valor arbitrario provocaría un 4xx legítimo, no un bug).
VALORES_ESPECIFICOS = {
    "modalidad": "De Cheque a OPF",
    "tipo": "4ta",
    "lineas": ["3154500;Aut.total;100"],
}


def _valor_para(nombre: str, anotacion: str):
    if nombre in VALORES_ESPECIFICOS:
        return VALORES_ESPECIFICOS[nombre]
    if "list[str]" in anotacion:
        return ["3154500"]
    if "list" in anotacion:
        return []
    if "dict" in anotacion:
        return FILA
    if "bool" in anotacion:
        return False
    if "int" in anotacion:
        return 1
    if "float" in anotacion:
        return 1.0
    return "3154500"


def _cuerpo(modelo) -> dict:
    """Construye un request body mínimo válido a partir del modelo Pydantic."""
    return {
        nombre: _valor_para(nombre, str(campo.annotation))
        for nombre, campo in modelo.model_fields.items()
        if campo.default is PydanticUndefined
    }


def _rutas(app):
    """Rutas /api sin parámetros de path, con su método y modelo de body."""
    for r in app.routes:
        path = getattr(r, "path", "")
        if not path.startswith("/api") or "{" in path:
            continue
        for metodo in sorted((getattr(r, "methods", None) or set()) - {"HEAD", "OPTIONS"}):
            yield metodo, path, getattr(r, "body_field", None)


@pytest.fixture(scope="module")
def cliente(tmp_path_factory):
    """App real con la BD sembrada, sin ningún mock."""
    import os

    from demo.seed import sembrar

    cwd = os.getcwd()
    os.chdir(tmp_path_factory.mktemp("demo"))
    try:
        sembrar()
        with TestClient(create_app()) as c:
            yield c
    finally:
        os.chdir(cwd)


def test_ningun_endpoint_responde_5xx(cliente):
    """Cada endpoint debe completar la cadena sin error de servidor."""
    fallos = []
    for metodo, path, body_field in _rutas(cliente.app):
        body = _cuerpo(body_field.type_) if body_field is not None else None
        try:
            resp = cliente.request(metodo, path, json=body)
        except Exception as exc:  # noqa: BLE001 — lo que buscamos es justamente esto
            fallos.append(f"{metodo} {path} -> {type(exc).__name__}: {exc}")
            continue
        if resp.status_code >= 500:
            fallos.append(f"{metodo} {path} -> {resp.status_code}: {resp.text[:200]}")

    assert not fallos, "endpoints con error de servidor:\n" + "\n".join(fallos)


def test_el_barrido_cubre_todos_los_routers(cliente):
    """Guardia del propio barrido: si baja la cobertura, algo dejó de registrarse."""
    paths = {path for _, path, _ in _rutas(cliente.app)}
    prefijos = {"/".join(p.split("/")[:3]) for p in paths}

    assert len(paths) >= 60
    assert prefijos >= {
        "/api/acceso", "/api/datos", "/api/descargas", "/api/procesos",
        "/api/mantenimiento", "/api/config", "/api/generar", "/api/mesa-ayuda",
    }
