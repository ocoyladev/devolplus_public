import asyncio

from MACRO.app.websocket import ConnectionManager


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)


def test_broadcast_envia_a_todos_los_clientes() -> None:
    async def run() -> tuple[FakeWS, FakeWS]:
        cm = ConnectionManager()
        a, b = FakeWS(), FakeWS()
        await cm.connect(a)
        await cm.connect(b)
        assert cm.count == 2
        await cm.broadcast({"type": "progress", "msg": "x"})
        return a, b

    a, b = asyncio.run(run())
    assert a.accepted and b.accepted
    assert a.sent == [{"type": "progress", "msg": "x"}]
    assert b.sent == [{"type": "progress", "msg": "x"}]


def test_disconnect_deja_de_recibir() -> None:
    async def run() -> FakeWS:
        cm = ConnectionManager()
        a = FakeWS()
        await cm.connect(a)
        cm.disconnect(a)
        await cm.broadcast({"msg": "y"})
        return a

    a = asyncio.run(run())
    assert a.sent == []
