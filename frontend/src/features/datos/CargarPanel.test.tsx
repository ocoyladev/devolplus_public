import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { CargarPanel } from "./CargarPanel";
import { datos } from "../../api/acciones";

vi.mock("../../api/acciones", () => ({
  datos: {
    cargar: vi.fn(async () => "job-1"),
    planeamientoEstado: vi.fn(async () => true),
  },
}));

afterEach(() => vi.clearAllMocks());

test("envía los num_docs parseados y notifica el job", async () => {
  const onJob = vi.fn();
  render(<CargarPanel onJobIniciado={onJob} onError={() => {}} />);

  fireEvent.click(screen.getByText("Cargar datos"));
  fireEvent.change(screen.getByLabelText("Números de documento"), {
    target: { value: "  111 \n\n 222 \n" },
  });
  fireEvent.click(screen.getByText("Cargar"));

  expect(datos.cargar).toHaveBeenCalledWith(["111", "222"]);
  await vi.waitFor(() => expect(onJob).toHaveBeenCalledWith("cargar_datos"));
});

test("deshabilita 'Archivo RSIRAT' cuando el planeamiento está bloqueado", async () => {
  vi.mocked(datos.planeamientoEstado).mockResolvedValueOnce(false);
  render(<CargarPanel onJobIniciado={() => {}} onError={() => {}} />);
  fireEvent.click(screen.getByText("Cargar datos"));
  await waitFor(() => {
    const input = screen
      .getByText("Archivo RSIRAT")
      .querySelector("input") as HTMLInputElement;
    expect(input.disabled).toBe(true);
  });
  // Los otros archivos siguen habilitados.
  const asignacion = screen
    .getByText("Archivo de asignación")
    .querySelector("input") as HTMLInputElement;
  expect(asignacion.disabled).toBe(false);
});

test("avisa si no hay documentos", () => {
  const onError = vi.fn();
  render(<CargarPanel onJobIniciado={() => {}} onError={onError} />);
  fireEvent.click(screen.getByText("Cargar datos"));
  fireEvent.click(screen.getByText("Cargar"));
  expect(onError).toHaveBeenCalled();
  expect(datos.cargar).not.toHaveBeenCalled();
});
