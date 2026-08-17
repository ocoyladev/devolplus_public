import { afterEach, expect, test, vi } from "vitest";

import { fetchHealth } from "./health";

afterEach(() => vi.restoreAllMocks());

test("fetchHealth devuelve el status del backend", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify({ status: "ok" }))),
  );
  await expect(fetchHealth()).resolves.toBe("ok");
});
