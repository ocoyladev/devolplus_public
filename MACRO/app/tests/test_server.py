from pathlib import Path

from fastapi.testclient import TestClient

from MACRO.app.server import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_serves_index_when_static_dir_given(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<!doctype html><title>DEVOL+</title>OK")
    client = TestClient(create_app(static_dir=tmp_path))
    resp = client.get("/")
    assert resp.status_code == 200
    assert "DEVOL+" in resp.text


def test_spa_fallback_for_unknown_path(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<!doctype html>APPSHELL")
    client = TestClient(create_app(static_dir=tmp_path))
    resp = client.get("/alguna/ruta/cliente")
    assert resp.status_code == 200
    assert "APPSHELL" in resp.text


def test_api_not_shadowed_by_static(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("APPSHELL")
    client = TestClient(create_app(static_dir=tmp_path))
    assert client.get("/api/health").json() == {"status": "ok"}


def test_ws_echo_pong() -> None:
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"type": "pong"}
