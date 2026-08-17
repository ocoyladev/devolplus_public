import { afterEach, expect, test, vi } from "vitest";

import { fetchTabla } from "./tabla";

afterEach(() => vi.restoreAllMocks());

test("fetchTabla devuelve columns/rows/total", async () => {
  const payload = { columns: ["num_doc"], rows: [{ num_doc: "1" }], total: 1 };
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(payload))),
  );
  await expect(fetchTabla()).resolves.toEqual(payload);
});

test("fetchTabla lanza en error HTTP", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("x", { status: 500 })));
  await expect(fetchTabla()).rejects.toThrow(/500/);
});
