import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { MasAccionesMenu } from "./MasAccionesMenu";
import { descargas } from "../../api/acciones";

vi.mock("../../api/acciones", () => ({
  descargas: {
    numeracion: vi.fn(async () => "job-1"),
    riMasivo: vi.fn(async () => "job-ri"),
    cartasMasivo: vi.fn(async () => "job-ca"),
    rsiratRef: vi.fn(async () => "job-ref"),
    rsiratAntecedentes: vi.fn(async () => "job-antec"),
    rsiratPreflight: vi.fn(),
  },
}));

const noop = (): void => {};

const FILAS_RSIRAT = [{ of_devolucion: "26001", num_ruc: "10", nombre: "A" }];

/** Abre el modal previo de "Descargar REF/Tiempos (RSIRAT)". */
function abrirModalRef(filas = FILAS_RSIRAT, onJob = noop): void {
  render(<MasAccionesMenu filas={filas} onJobIniciado={onJob} onError={noop} />);
  fireEvent.click(screen.getByText("Más acciones ▾"));
  fireEvent.click(screen.getByText("Descargar REF/Tiempos (RSIRAT)"));
}

test("botón deshabilitado sin selección", () => {
  render(<MasAccionesMenu filas={[]} onJobIniciado={noop} onError={noop} />);
  expect(screen.getByText("Más acciones ▾")).toBeDisabled();
});

test("Registrar cartas genera una línea OF,RUC,Expediente por fila", () => {
  const filas = [
    { of_devolucion: "250023006919", num_ruc: "10316187447", num_dev: "0023244705346" },
    { of_devolucion: "250023006920", ruc: "10111111112", num_dev: "0023244705347" },
  ];
  render(<MasAccionesMenu filas={filas} onJobIniciado={noop} onError={noop} />);
  fireEvent.click(screen.getByText("Más acciones ▾"));
  fireEvent.click(screen.getByText("Registrar cartas"));

  const ta = screen.getByRole("textbox") as HTMLTextAreaElement;
  expect(ta.value).toBe(
    "250023006919,10316187447,0023244705346\n250023006920,10111111112,0023244705347",
  );
});

test("Agregar numeración llama a la API con las filas y notifica el job", async () => {
  const filas = [{ num_doc: "1", carta: "78954-2026" }];
  const onJob = vi.fn();
  render(<MasAccionesMenu filas={filas} onJobIniciado={onJob} onError={noop} />);
  fireEvent.click(screen.getByText("Más acciones ▾"));
  fireEvent.click(screen.getByText("Agregar numeración"));

  expect(descargas.numeracion).toHaveBeenCalledWith(filas);
  await waitFor(() => expect(onJob).toHaveBeenCalledWith("numeracion_cartas"));
});

test("Descargar cartas (selección) llama a cartasMasivo con filas + archivo", async () => {
  const filas = [{ num_doc: "1", carta: "78954-2026" }];
  const onJob = vi.fn();
  render(<MasAccionesMenu filas={filas} archivo={true} onJobIniciado={onJob} onError={noop} />);
  fireEvent.click(screen.getByText("Más acciones ▾"));
  fireEvent.click(screen.getByText("Descargar cartas (selección)"));

  expect(descargas.cartasMasivo).toHaveBeenCalledWith(filas, true);
  await waitFor(() => expect(onJob).toHaveBeenCalledWith("descarga_cartas_masivo"));
});

test("Descargar RI (selección) llama a riMasivo con filas + archivo", async () => {
  const filas = [{ num_doc: "1", num_ri: "RI-1" }];
  const onJob = vi.fn();
  render(<MasAccionesMenu filas={filas} onJobIniciado={onJob} onError={noop} />);
  fireEvent.click(screen.getByText("Más acciones ▾"));
  fireEvent.click(screen.getByText("Descargar RI (selección)"));

  expect(descargas.riMasivo).toHaveBeenCalledWith(filas, false);
  await waitFor(() => expect(onJob).toHaveBeenCalledWith("descarga_ri"));
});

test("RSIRAT: el modal previo consulta el preflight y deshabilita Iniciar sin pendientes", async () => {
  vi.mocked(descargas.rsiratPreflight).mockResolvedValue({
    tipo: "ref",
    total: 1,
    pendientes: 0,
    casos: [
      {
        of: "26001",
        ruc: "10",
        carpeta: "D:\\DEVOL\\26001_10_A",
        estado: "omitido",
        existentes: ["REF.pdf", "Reporte de Tareas.pdf"],
        faltantes: [],
        detalle: "ya descargado",
      },
    ],
  });

  abrirModalRef();

  expect(descargas.rsiratPreflight).toHaveBeenCalledWith("ref", FILAS_RSIRAT);
  await waitFor(() =>
    expect(screen.getByText(/No hay descargas pendientes/)).toBeInTheDocument(),
  );
  expect(screen.getByText("Iniciar")).toBeDisabled();
  expect(screen.getByText(/ya descargado/)).toBeInTheDocument();
  expect(screen.getByText(/0 de 1 caso\(s\) con descargas pendientes/)).toBeInTheDocument();
});

test("RSIRAT: con pendientes se puede iniciar y se anuncia el hotkey de aborto", async () => {
  vi.mocked(descargas.rsiratPreflight).mockResolvedValue({
    tipo: "ref",
    total: 1,
    pendientes: 1,
    casos: [
      {
        of: "26001",
        ruc: "10",
        carpeta: "D:\\DEVOL\\26001_10_A",
        estado: "pendiente",
        existentes: ["REF.pdf"],
        faltantes: ["Reporte de Tareas"],
        detalle: "falta Reporte de Tareas",
      },
    ],
  });
  const onJob = vi.fn();

  abrirModalRef(FILAS_RSIRAT, onJob);

  await waitFor(() => expect(screen.getByText("Iniciar")).toBeEnabled());
  expect(screen.getByText(/Ctrl\+Shift\+Q/)).toBeInTheDocument();
  expect(screen.getByText(/pendiente — falta Reporte de Tareas/)).toBeInTheDocument();

  fireEvent.click(screen.getByText("Iniciar"));
  expect(descargas.rsiratRef).toHaveBeenCalledWith(FILAS_RSIRAT);
  await waitFor(() => expect(onJob).toHaveBeenCalledWith("rsirat_ref"));
});

test("RSIRAT: si el preflight falla se avisa y se permite iniciar igual", async () => {
  vi.mocked(descargas.rsiratPreflight).mockRejectedValue(new Error("Error 500"));

  abrirModalRef();

  await waitFor(() =>
    expect(screen.getByText(/No se pudo verificar los archivos existentes/)).toBeInTheDocument(),
  );
  expect(screen.getByText("Iniciar")).toBeEnabled();
});
