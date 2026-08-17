from unittest.mock import patch

from fastapi.testclient import TestClient

from MACRO.app.schemas.entorno import FirmaAutoEstado
from MACRO.app.server import create_app

DETECTAR = "MACRO.app.routers.entorno._detectar_pantalla"


def test_firma_auto_no_windows_deshabilitada() -> None:
    # En el entorno de CI (Linux) la detección no está disponible.
    client = TestClient(create_app())
    resp = client.get("/api/entorno/firma-auto")
    assert resp.status_code == 200
    data = resp.json()
    assert data["disponible"] is False
    assert data["motivo"]


def test_firma_auto_disponible_cuando_coincide() -> None:
    estado = FirmaAutoEstado(
        disponible=True, escala=125, ancho=1920, alto=1200, motivo="",
        perfil="125@1920x1200",
    )
    with patch(DETECTAR, return_value=estado):
        client = TestClient(create_app())
        resp = client.get("/api/entorno/firma-auto")
    assert resp.json() == {
        "disponible": True,
        "escala": 125,
        "ancho": 1920,
        "alto": 1200,
        "motivo": "",
        "perfil": "125@1920x1200",
    }


def test_firma_auto_disponible_perfil_1080() -> None:
    estado = FirmaAutoEstado(
        disponible=True, escala=100, ancho=1920, alto=1080, motivo="",
        perfil="100@1920x1080",
    )
    with patch(DETECTAR, return_value=estado):
        client = TestClient(create_app())
        resp = client.get("/api/entorno/firma-auto")
    assert resp.json()["perfil"] == "100@1920x1080"


def test_firma_auto_no_disponible_por_resolucion() -> None:
    estado = FirmaAutoEstado(
        disponible=False, escala=125, ancho=1536, alto=864,
        motivo="Requiere escala 125% y resolución 1920×1200 (detectado: 125% y 1536×864).",
    )
    with patch(DETECTAR, return_value=estado):
        client = TestClient(create_app())
        resp = client.get("/api/entorno/firma-auto")
    data = resp.json()
    assert data["disponible"] is False
    assert "1920" in data["motivo"]
