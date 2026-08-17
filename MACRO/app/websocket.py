"""Gestor de conexiones WebSocket y difusión de eventos de progreso."""
from __future__ import annotations

from typing import Protocol


class _Socket(Protocol):
    async def accept(self) -> None: ...
    async def send_json(self, data: dict) -> None: ...


class ConnectionManager:
    """Mantiene los clientes WS conectados y difunde mensajes a todos."""

    def __init__(self) -> None:
        self._clients: set[_Socket] = set()

    async def connect(self, socket: _Socket) -> None:
        await socket.accept()
        self._clients.add(socket)

    def disconnect(self, socket: _Socket) -> None:
        self._clients.discard(socket)

    async def broadcast(self, message: dict) -> None:
        for socket in list(self._clients):
            try:
                await socket.send_json(message)
            except Exception:  # noqa: BLE001 — cliente caído: se descarta
                self._clients.discard(socket)

    @property
    def count(self) -> int:
        return len(self._clients)
