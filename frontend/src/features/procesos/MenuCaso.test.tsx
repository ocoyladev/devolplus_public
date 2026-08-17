import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { MenuCaso } from "./MenuCaso";
import { descargas, itop } from "../../api/acciones";

vi.mock("../../api/acciones", () => ({
  descargas: {
    expElectronico: vi.fn(async () => "j"),
    echasqui: vi.fn(async () => "j"),
    tresUit: vi.fn(async () => "j"),
    porEjercicios: vi.fn(async () => "j"),
  },
  itop: {
    descarga: vi.fn(async () => "j"),
    modificar: vi.fn(async () => "j"),
    empleadores601: vi.fn(async () => ({ empleadores: [] })),
    preview: vi.fn(async () => ({
      tipo: "4ta", of: "OF1", ruc: "10111111112", nombre: "PEPE",
      periodo_ini: 202401, periodo_fin: 202412,
      contenido_txt: "10111111112|202401|202412|", titulo: "t",
    })),
  },
  abrir: {
    carpeta: vi.fn(async () => undefined),
    macro: vi.fn(async () => undefined),
  },
}));

afterEach(() => vi.clearAllMocks());

test("Exp. Electrónico dispara la descarga con la fila seleccionada", async () => {
  const onJob = vi.fn();
  render(<MenuCaso row={{ num_doc: "1" }} onJobIniciado={onJob} onError={() => {}} />);

  fireEvent.click(screen.getByText("Acciones del caso ▾"));
  fireEvent.click(screen.getByText("Exp. Electrónico"));

  expect(descargas.expElectronico).toHaveBeenCalledWith({ num_doc: "1" });
  await vi.waitFor(() => expect(onJob).toHaveBeenCalledWith("descarga_exp"));
});

test("todas las acciones del caso están habilitadas", () => {
  render(<MenuCaso row={{ num_doc: "1" }} onJobIniciado={() => {}} onError={() => {}} />);
  fireEvent.click(screen.getByText("Acciones del caso ▾"));
  expect(screen.getByText("Carta")).toBeEnabled();
  expect(screen.getByText("Por ejercicio(s)")).toBeEnabled();
  expect(screen.getByText("Rentas 4ta")).toBeEnabled();
});

test("Rentas 4ta abre el modal y al confirmar lanza la descarga", async () => {
  const onJob = vi.fn();
  render(
    <MenuCaso
      row={{ num_doc: "1", ruc: "10111111112", of_devolucion: "OF1", per_doc: "202412" }}
      onJobIniciado={onJob}
      onError={() => {}}
    />,
  );
  fireEvent.click(screen.getByText("Acciones del caso ▾"));
  fireEvent.click(screen.getByText("Rentas 4ta"));
  // El modal aparece; confirmar dispara itop.descarga con tipo 4ta.
  fireEvent.click(await screen.findByText("Confirmar y enviar"));
  await vi.waitFor(() =>
    expect(itop.descarga).toHaveBeenCalledWith("4ta", expect.any(Object), {}));
});

test("existe el ítem PDT 601 - empleador completo", () => {
  render(<MenuCaso row={{ num_doc: "1" }} onJobIniciado={() => {}} onError={() => {}} />);
  fireEvent.click(screen.getByText("Acciones del caso ▾"));
  expect(screen.getByText("PDT 601 - empleador completo")).toBeInTheDocument();
});
