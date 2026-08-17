import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { Toolbar } from "./Toolbar";
import { procesos } from "../../api/acciones";

vi.mock("../../api/acciones", () => ({
  procesos: {
    archivar: vi.fn(async () => "job-1"),
    recuperar: vi.fn(async () => "job-2"),
    papeles_trabajo: vi.fn(async () => "job-3"),
    cargaExpedientes: vi.fn(async () => "job-4"),
    autorizar: vi.fn(async () => "job-5"),
    archivarRepositorio: vi.fn(async () => "job-6"),
  },
}));

afterEach(() => vi.clearAllMocks());

test("botones deshabilitados sin selección", () => {
  render(
    <Toolbar
      seleccion={[]}
      filas={[]}
      firmaAutoDisponible={false}
      firmaAutoMotivo=""
      archivo={false}
      onJobIniciado={() => {}}
      onError={() => {}}
    />,
  );
  expect(screen.getByText("Archivar")).toBeDisabled();
  expect(screen.getByText("Generar PAPELES_TRABAJO")).toBeDisabled();
});

test("Archivar invoca procesos.archivar con la selección y notifica el job", async () => {
  const onJob = vi.fn();
  render(
    <Toolbar
      seleccion={["1", "2"]}
      filas={[]}
      firmaAutoDisponible={false}
      firmaAutoMotivo=""
      archivo={false}
      onJobIniciado={onJob}
      onError={() => {}}
    />,
  );
  fireEvent.click(screen.getByText("Archivar"));
  expect(procesos.archivar).toHaveBeenCalledWith(["1", "2"]);
  await vi.waitFor(() => expect(onJob).toHaveBeenCalledWith("archivar"));
});

test("Archivar REPOSITORIO invoca procesos.archivarRepositorio con la selección", async () => {
  const onJob = vi.fn();
  render(
    <Toolbar
      seleccion={["1", "2"]}
      filas={[]}
      firmaAutoDisponible={false}
      firmaAutoMotivo=""
      archivo={false}
      onJobIniciado={onJob}
      onError={() => {}}
    />,
  );
  fireEvent.click(screen.getByText("Archivar REPOSITORIO"));
  expect(procesos.archivarRepositorio).toHaveBeenCalledWith(["1", "2"]);
  await vi.waitFor(() => expect(onJob).toHaveBeenCalledWith("archivar_repositorio"));
});
