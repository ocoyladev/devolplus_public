import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { MantenimientoPanel } from "./MantenimientoPanel";
import * as api from "../../api/mantenimiento";
import { datos } from "../../api/acciones";

function fila(over: Partial<api.DescargaCola> = {}): api.DescargaCola {
  return {
    id: 1,
    num_doc: "D1",
    ruc: "10",
    tipo_servicio: "PORTAL",
    tipo_descarga: "RI",
    parametro: "RI-1",
    estado: "PENDIENTE",
    reintentos: 0,
    error_log: "",
    ...over,
  };
}

vi.mock("../../api/acciones", () => ({
  datos: { planeamientoEstado: vi.fn(async () => true) },
}));

vi.mock("../../api/mantenimiento", () => ({
  listarDescargas: vi.fn(async () => ({
    descargas: [
      {
        id: 1,
        num_doc: "D1",
        ruc: "10",
        tipo_servicio: "PORTAL",
        tipo_descarga: "RI",
        parametro: "RI-1",
        estado: "PENDIENTE",
        reintentos: 0,
        error_log: "",
      },
    ],
  })),
  eliminarDescargas: vi.fn(async () => ({ eliminadas: 1 })),
  ejecutarDescargas: vi.fn(async () => ({ job_id: "j1" })),
  borrarBd: vi.fn(async () => ({ ok: true })),
  borrarDescargas: vi.fn(async () => ({ ok: true })),
}));

afterEach(() => vi.clearAllMocks());

function onRecalcularStub(): ReturnType<typeof vi.fn> {
  return vi
    .fn()
    .mockResolvedValue({ disponible: true, motivo: "", perfil: "125@1920x1200" });
}

test("lista descargas al abrir el panel", async () => {
  render(
    <MantenimientoPanel
      onAviso={() => {}}
      onJobIniciado={() => {}}
      onRecalcularPantalla={onRecalcularStub()}
    />,
  );
  fireEvent.click(screen.getByLabelText("Mantenimiento")); // ícono ⚙
  fireEvent.click(screen.getByText("Descargas")); // opción del menú
  await screen.findByText("RI-1");
});

test("deshabilita la fila de planeamiento en horario laboral", async () => {
  vi.mocked(api.listarDescargas).mockResolvedValueOnce({
    descargas: [
      fila({ id: 1, tipo_descarga: "RI", parametro: "RI-1" }),
      fila({ id: 2, tipo_descarga: "PLANEAMIENTO", parametro: "PLAN-2" }),
    ],
  });
  vi.mocked(datos.planeamientoEstado).mockResolvedValueOnce(false);

  render(
    <MantenimientoPanel
      onAviso={() => {}}
      onJobIniciado={() => {}}
      onRecalcularPantalla={onRecalcularStub()}
    />,
  );
  fireEvent.click(screen.getByLabelText("Mantenimiento"));
  fireEvent.click(screen.getByText("Descargas"));
  await screen.findByText("PLAN-2");

  // La casilla de la fila de planeamiento (id 2) queda deshabilitada.
  await waitFor(() => {
    expect(screen.getByLabelText("Seleccionar 2")).toBeDisabled();
  });
  // La fila que no es planeamiento sigue habilitada.
  expect(screen.getByLabelText("Seleccionar 1")).toBeEnabled();
});

test("Borrar BD está deshabilitado hasta escribir el texto exacto", async () => {
  render(
    <MantenimientoPanel
      onAviso={() => {}}
      onJobIniciado={() => {}}
      onRecalcularPantalla={onRecalcularStub()}
    />,
  );
  fireEvent.click(screen.getByLabelText("Mantenimiento"));
  fireEvent.click(screen.getByText("Borrado"));

  const boton = screen.getByText("Borrar BD");
  expect(boton).toBeDisabled();

  fireEvent.change(screen.getByPlaceholderText("Escriba: BORRAR BD"), {
    target: { value: "BORRAR BD" },
  });
  expect(boton).toBeEnabled();
  fireEvent.click(boton);
  await waitFor(() => expect(api.borrarBd).toHaveBeenCalled());
});

test("Recalcular pantalla avisa el perfil detectado", async () => {
  const onAviso = vi.fn();
  const onRecalcular = vi
    .fn()
    .mockResolvedValue({ disponible: true, motivo: "", perfil: "125@1920x1200" });
  render(
    <MantenimientoPanel
      onAviso={onAviso}
      onJobIniciado={vi.fn()}
      onRecalcularPantalla={onRecalcular}
    />,
  );
  fireEvent.click(screen.getByLabelText("Mantenimiento"));
  fireEvent.click(screen.getByText("Recalcular pantalla"));
  await waitFor(() => expect(onRecalcular).toHaveBeenCalledTimes(1));
  await waitFor(() =>
    expect(onAviso).toHaveBeenCalledWith(expect.stringContaining("125@1920x1200")),
  );
});
