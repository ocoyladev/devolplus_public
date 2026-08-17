import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { ConfigPanel } from "./ConfigPanel";
import * as api from "../../api/config";

vi.mock("../../api/config", () => ({
  getRutas: vi.fn(async () => ({
    PATH_DESCARGAS: "D:/D",
    PATH_RI: "D:/RI",
    PATH_AUTORIZAR: "D:/A",
    PATH_ARCHIVO: "D:/AR",
    UNIDAD_ORGANICA_FOLIO: "7EC400",
  })),
  getLicencia: vi.fn(async () => ({ valida: true, usuario: "u", mensaje: "ok" })),
  getCredenciales: vi.fn(async (sistema: string) => ({
    sistema,
    usuario: sistema === "Portal" ? "jdoe" : "fuser",
  })),
  putRutas: vi.fn(async () => ({})),
  putCredenciales: vi.fn(async () => ({ sistema: "Portal", usuario: "u" })),
  registrarLicencia: vi.fn(async () => ({ ok: true, mensaje: "ok" })),
  seleccionarCarpeta: vi.fn(async () => "D:/NUEVA"),
  getFeriados: vi.fn(async () => ({ feriados: [] })),
  addFeriado: vi.fn(async () => ({ feriados: [] })),
  delFeriado: vi.fn(async () => ({ feriados: [] })),
}));

afterEach(() => vi.clearAllMocks());

test("el botón se llama 'Configuración' y muestra el folio 7EC400", async () => {
  render(<ConfigPanel onAviso={() => {}} />);
  fireEvent.click(screen.getByText("Configuración"));
  await screen.findByDisplayValue("7EC400");
});

test("carga el usuario registrado de cada sistema", async () => {
  render(<ConfigPanel onAviso={() => {}} />);
  fireEvent.click(screen.getByText("Configuración"));
  await screen.findByDisplayValue("jdoe");
  await screen.findByDisplayValue("fuser");
});

test("guarda credenciales del sistema con su usuario", async () => {
  render(<ConfigPanel onAviso={() => {}} />);
  fireEvent.click(screen.getByText("Configuración"));
  await screen.findByDisplayValue("jdoe");

  fireEvent.click(screen.getByText("Guardar Portal"));
  await waitFor(() =>
    expect(api.putCredenciales).toHaveBeenCalledWith("Portal", "jdoe", ""),
  );
});
