import { afterEach, expect, test, vi } from "vitest";

import { abrir, descargas, procesos } from "./acciones";

afterEach(() => vi.restoreAllMocks());

test("procesos.archivar postea num_docs y devuelve job_id", async () => {
  const fetchMock = vi.fn(
    async (_url: string, _init: RequestInit) =>
      new Response(JSON.stringify({ job_id: "j1" })),
  );
  vi.stubGlobal("fetch", fetchMock);

  const id = await procesos.archivar(["1", "2"]);
  expect(id).toBe("j1");
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/procesos/archivar");
  expect(JSON.parse(init.body as string)).toEqual({ num_docs: ["1", "2"] });
});

test("descargas.ri postea la fila con archivo", async () => {
  const fetchMock = vi.fn(
    async (_url: string, _init: RequestInit) =>
      new Response(JSON.stringify({ job_id: "j2" })),
  );
  vi.stubGlobal("fetch", fetchMock);

  await descargas.ri({ num_doc: "9", num_ri: "RI-1" }, true);
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/descargas/ri");
  expect(JSON.parse(init.body as string)).toEqual({
    row: { num_doc: "9", num_ri: "RI-1" },
    archivo: true,
  });
});

test("descargas.cartasMasivo postea filas + archivo", async () => {
  const fetchMock = vi.fn(
    async (_url: string, _init: RequestInit) =>
      new Response(JSON.stringify({ job_id: "j3" })),
  );
  vi.stubGlobal("fetch", fetchMock);

  await descargas.cartasMasivo([{ num_doc: "1" }, { num_doc: "2" }], true);
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/descargas/cartas-masivo");
  expect(JSON.parse(init.body as string)).toEqual({
    filas: [{ num_doc: "1" }, { num_doc: "2" }],
    archivo: true,
  });
});

test("abrir.carpeta lanza en error", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("nope", { status: 404 })));
  await expect(abrir.carpeta({ num_doc: "1" })).rejects.toThrow(/404/);
});

test("procesos.validarArchivo devuelve casos del backend", async () => {
  const casos = [{ num_doc: "D1", nivel: "ok", alertas: [] }];
  const fetchMock = vi.fn(
    async (_url: string, _init: RequestInit) =>
      new Response(JSON.stringify({ casos })),
  );
  vi.stubGlobal("fetch", fetchMock);

  const out = await procesos.validarArchivo(["D1"]);
  expect(out[0].num_doc).toBe("D1");
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/procesos/validar-archivo");
  expect(JSON.parse(init.body as string)).toEqual({ num_docs: ["D1"] });
});
