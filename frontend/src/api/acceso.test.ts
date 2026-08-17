import { afterEach, expect, test, vi } from "vitest";

import { getAcceso, solicitarAcceso } from "./acceso";

afterEach(() => vi.restoreAllMocks());

test("getAcceso consulta /api/acceso", async () => {
  const fetchMock = vi.fn(
    async (_url: string) =>
      new Response(
        JSON.stringify({ estado: "permitido", usuario_red: "u", mensaje: "ok" }),
      ),
  );
  vi.stubGlobal("fetch", fetchMock);

  const r = await getAcceso();
  expect(r.estado).toBe("permitido");
  expect(fetchMock.mock.calls[0][0]).toBe("/api/acceso");
});

test("solicitarAcceso postea nombre y email", async () => {
  const fetchMock = vi.fn(
    async (_url: string, _init: RequestInit) =>
      new Response(JSON.stringify({ ok: true, mensaje: "Solicitud registrada." })),
  );
  vi.stubGlobal("fetch", fetchMock);

  const r = await solicitarAcceso("Juan Doe", "jdoe@example.org");
  expect(r.ok).toBe(true);
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/acceso/solicitud");
  expect(JSON.parse(init.body as string)).toEqual({
    nombre_completo: "Juan Doe",
    email: "jdoe@example.org",
  });
});
