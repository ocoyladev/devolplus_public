import { afterEach, expect, test, vi } from "vitest";

import { putCredenciales, putRutas } from "./config";

afterEach(() => vi.restoreAllMocks());

test("putRutas hace PUT con solo las rutas provistas", async () => {
  const fetchMock = vi.fn(
    async (_url: string, _init: RequestInit) => new Response(JSON.stringify({})),
  );
  vi.stubGlobal("fetch", fetchMock);

  await putRutas({ PATH_RI: "D:/RI" });
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/config/rutas");
  expect(init.method).toBe("PUT");
  expect(JSON.parse(init.body as string)).toEqual({ PATH_RI: "D:/RI" });
});

test("putCredenciales envía sistema/usuario/password", async () => {
  const fetchMock = vi.fn(
    async (_url: string, _init: RequestInit) =>
      new Response(JSON.stringify({ sistema: "Portal", usuario: "u" })),
  );
  vi.stubGlobal("fetch", fetchMock);

  await putCredenciales("Portal", "u", "p");
  const [, init] = fetchMock.mock.calls[0];
  expect(JSON.parse(init.body as string)).toEqual({
    sistema: "Portal",
    usuario: "u",
    password: "p",
  });
});
