import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import App from "./App";

afterEach(() => vi.restoreAllMocks());

function mockFetch(tablaResp: () => Response): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL | Request) => {
      const u = String(url);
      if (u.includes("/api/acceso")) {
        return new Response(
          JSON.stringify({ estado: "permitido", usuario_red: "u", mensaje: "ok" }),
        );
      }
      return tablaResp();
    }),
  );
}

test("con acceso permitido y sin casos muestra el mensaje vacío", async () => {
  mockFetch(() => new Response(JSON.stringify({ columns: [], rows: [], total: 0 })));
  render(<App />);
  await waitFor(() =>
    expect(screen.getByText(/no hay casos cargados/i)).toBeInTheDocument(),
  );
});

test("muestra la autoría en el pie de página", async () => {
  mockFetch(() => new Response(JSON.stringify({ columns: [], rows: [], total: 0 })));
  render(<App />);
  await waitFor(() =>
    expect(screen.getByText(/Oscar Arnold Coyla Urquizo/i)).toBeInTheDocument(),
  );
});

test("usuario no registrado ve el formulario de solicitud de acceso", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            estado: "no_registrado",
            usuario_red: "u",
            mensaje: "No tiene acceso registrado.",
          }),
        ),
    ),
  );
  render(<App />);
  await waitFor(() =>
    expect(screen.getByText(/solicitar acceso/i)).toBeInTheDocument(),
  );
});

test("usuario pendiente ve el mensaje para contactar al autor", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            estado: "pendiente",
            usuario_red: "u",
            mensaje: "Su solicitud está pendiente. Contacte al administrador.",
          }),
        ),
    ),
  );
  render(<App />);
  await waitFor(() =>
    expect(screen.getByText(/pendiente/i)).toBeInTheDocument(),
  );
});
