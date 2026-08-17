from unittest.mock import patch

from fastapi.testclient import TestClient

from MACRO.app.server import create_app

_CARTA = {
    "id": 7, "num_doc": "D1", "numero": "78954", "anio": "2026",
    "tipo": "PRIMERA", "fecha_emision": "10/08/2026",
    "fecha_notificacion": "14/08/2026", "plazo": 3,
    "fecha_vencimiento": "19/08/2026", "vencimiento_manual": 0,
    "atendida": 0, "obs": "", "estado": "VIGENTE",
}


def test_get_cartas_devuelve_la_lista() -> None:
    with patch(
        "MACRO.funciones.funciones_registro_cartas.listar_cartas", return_value=[_CARTA]
    ) as m:
        client = TestClient(create_app())
        resp = client.get("/api/cartas/D1")
    assert resp.status_code == 200
    assert resp.json()["cartas"][0]["numero"] == "78954"
    m.assert_called_once_with("D1")


def test_post_crea_carta() -> None:
    with patch(
        "MACRO.funciones.funciones_registro_cartas.caso_existe", return_value=True
    ), patch(
        "MACRO.funciones.funciones_registro_cartas.crear_carta", return_value=_CARTA
    ) as m:
        client = TestClient(create_app())
        resp = client.post(
            "/api/cartas/D1",
            json={"numero": "78954", "anio": "2026", "tipo": "PRIMERA", "plazo": 3},
        )
    assert resp.status_code == 200
    assert resp.json()["estado"] == "VIGENTE"
    assert m.call_args.args == ("D1",)
    assert m.call_args.kwargs["numero"] == "78954"
    assert "obs" not in m.call_args.kwargs  # los no enviados no se tocan


def test_post_num_doc_inexistente_devuelve_404() -> None:
    with patch(
        "MACRO.funciones.funciones_registro_cartas.caso_existe", return_value=False
    ):
        client = TestClient(create_app())
        resp = client.post("/api/cartas/NO_EXISTE", json={"numero": "1"})
    assert resp.status_code == 404


def test_patch_actualiza_carta() -> None:
    with patch(
        "MACRO.funciones.funciones_registro_cartas.actualizar_carta", return_value=_CARTA
    ) as m:
        client = TestClient(create_app())
        resp = client.patch("/api/cartas/7", json={"fecha_notificacion": "14/08/2026"})
    assert resp.status_code == 200
    m.assert_called_once_with(7, fecha_notificacion="14/08/2026")


def test_patch_id_inexistente_devuelve_404() -> None:
    with patch(
        "MACRO.funciones.funciones_registro_cartas.actualizar_carta", return_value=None
    ):
        client = TestClient(create_app())
        resp = client.patch("/api/cartas/999", json={"plazo": 3})
    assert resp.status_code == 404


def test_delete_carta() -> None:
    with patch(
        "MACRO.funciones.funciones_registro_cartas.eliminar_carta", return_value=True
    ) as m:
        client = TestClient(create_app())
        resp = client.delete("/api/cartas/7")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    m.assert_called_once_with(7)


def test_delete_id_inexistente_devuelve_404() -> None:
    with patch(
        "MACRO.funciones.funciones_registro_cartas.eliminar_carta", return_value=False
    ):
        client = TestClient(create_app())
        resp = client.delete("/api/cartas/999")
    assert resp.status_code == 404


def test_fecha_mal_formada_es_rechazada() -> None:
    client = TestClient(create_app())
    resp = client.post("/api/cartas/D1", json={"fecha_emision": "2026-08-10"})
    assert resp.status_code == 422

    # Fecha con formato correcto pero imposible (31 de febrero no existe).
    resp = client.post("/api/cartas/D1", json={"fecha_emision": "31/02/2026"})
    assert resp.status_code == 422


def test_plazo_no_positivo_es_rechazado() -> None:
    client = TestClient(create_app())
    resp = client.post("/api/cartas/D1", json={"plazo": 0})
    assert resp.status_code == 422


def test_tipo_invalido_es_rechazado() -> None:
    client = TestClient(create_app())
    resp = client.post("/api/cartas/D1", json={"tipo": "INVENTADO"})
    assert resp.status_code == 422


def test_fecha_vacia_es_valida() -> None:
    with patch(
        "MACRO.funciones.funciones_registro_cartas.caso_existe", return_value=True
    ), patch(
        "MACRO.funciones.funciones_registro_cartas.crear_carta", return_value=_CARTA
    ) as m:
        client = TestClient(create_app())
        resp = client.post("/api/cartas/D1", json={"fecha_vencimiento": ""})
    assert resp.status_code == 200
    assert m.call_args.kwargs["fecha_vencimiento"] == ""


def test_fallo_de_db_devuelve_500() -> None:
    with patch(
        "MACRO.funciones.funciones_registro_cartas.caso_existe", return_value=True
    ), patch(
        "MACRO.funciones.funciones_registro_cartas.crear_carta",
        side_effect=RuntimeError("db bloqueada"),
    ):
        client = TestClient(create_app(), raise_server_exceptions=False)
        resp = client.post("/api/cartas/D1", json={"numero": "1"})
    assert resp.status_code == 500
