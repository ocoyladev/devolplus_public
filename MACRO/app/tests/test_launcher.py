import socket

from MACRO.app.launcher import pick_free_port


def test_pick_free_port_returns_bindable_port() -> None:
    port = pick_free_port(start=8080)
    assert 8080 <= port < 65536
    # El puerto devuelto debe ser realmente enlazable.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", port))


def test_pick_free_port_skips_busy_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        busy.bind(("127.0.0.1", 0))
        busy_port = busy.getsockname()[1]
        busy.listen()
        chosen = pick_free_port(start=busy_port)
        assert chosen != busy_port
