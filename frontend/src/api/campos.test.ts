import { afterEach, expect, test, vi } from "vitest";

import { actualizarCampo } from "./campos";

afterEach(() => vi.restoreAllMocks());

test("actualizarCampo hace PATCH con campo/valor y num_doc en la URL", async () => {
  const fetchMock = vi.fn(
    async (_url: string, _init: RequestInit) =>
      new Response(JSON.stringify({ ok: true })),
  );
  vi.stubGlobal("fetch", fetchMock);

  await actualizarCampo("123-ABC", "resultado", "DENEGADO");

  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/campos/123-ABC");
  expect(init.method).toBe("PATCH");
  expect(JSON.parse(init.body as string)).toEqual({
    campo: "resultado",
    valor: "DENEGADO",
  });
});

test("actualizarCampo lanza en error HTTP", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("x", { status: 500 })));
  await expect(actualizarCampo("1", "carta", "C-1")).rejects.toThrow(/500/);
});
